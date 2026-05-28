"""Summarizer agent — Bedrock Claude Haiku plain-English summary."""

from __future__ import annotations

import json
import os
from typing import Any, cast
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

from service.agents.bedrock_util import invoke_claude_json, load_bedrock_config
from service.agents.summarizer.prompts import SYSTEM_PROMPT, build_user_prompt
from service.common.errors import PipelineError
from service.common.logging import get_logger
from service.common.models import (
    AgentName,
    AnalyzerOutput,
    FailureReason,
    FhirComposerOutput,
    SummarizerCitation,
    SummarizerFinding,
    SummarizerOutput,
)
from service.common.pipeline import agent_name_from_env, track_agent_run

logger = get_logger(__name__)

MAX_TOKENS = 512
TEMPERATURE = 0.2
JOB_TOKEN_BUDGET = int(os.environ.get("JOB_TOKEN_BUDGET", "2048"))


def _load_bundle(bundle_s3_url: str) -> dict[str, Any]:
    parsed = urlparse(bundle_s3_url)
    if parsed.scheme != "s3":
        raise PipelineError(FailureReason.S3_WRITE_FAILED, "bundle_s3_url must be s3://")
    try:
        obj = boto3.client("s3").get_object(Bucket=parsed.netloc, Key=parsed.path.lstrip("/"))
        return cast(dict[str, Any], json.loads(obj["Body"].read()))
    except ClientError as err:
        raise PipelineError(
            FailureReason.UNREACHABLE_VCF,
            "unable to read FHIR bundle from S3",
            cause=err,
        ) from err


def _stub_output(analyzer: AnalyzerOutput) -> SummarizerOutput:
    if not analyzer.calls:
        return SummarizerOutput(
            summary="No pharmacogenomic findings were available for summarization.",
            key_findings=[],
            citations=[],
            confidence=0.3,
        )
    call = analyzer.calls[0]
    drug = call.cpic_recommendations[0].drug if call.cpic_recommendations else "unknown"
    citation = (
        call.cpic_recommendations[0].citation
        if call.cpic_recommendations
        else "CPIC guideline unavailable"
    )
    return SummarizerOutput(
        summary=(
            f"Deterministic stub summary for {call.gene} ({call.phenotype}). "
            "Bedrock is disabled via feature flag."
        ),
        key_findings=[
            SummarizerFinding(gene=call.gene, phenotype=call.phenotype, drug=drug),
        ],
        citations=[SummarizerCitation(source="CPIC", guideline=citation)],
        confidence=0.85,
    )


def _invoke_summarizer(model_id: str, user_prompt: str) -> SummarizerOutput:
    last_error: PipelineError | None = None
    for attempt in range(2):
        try:
            result = invoke_claude_json(
                model_id=model_id,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            )
            if result.tokens_used > JOB_TOKEN_BUDGET:
                raise PipelineError(
                    FailureReason.TOKEN_BUDGET_EXCEEDED,
                    f"token budget exceeded ({result.tokens_used}>{JOB_TOKEN_BUDGET})",
                )
            return SummarizerOutput.model_validate(result.payload)
        except PipelineError as err:
            if err.reason != FailureReason.INVALID_LLM_OUTPUT or attempt == 1:
                raise
            last_error = err
    raise last_error or PipelineError(
        FailureReason.INVALID_LLM_OUTPUT,
        "summarizer output failed schema validation",
    )


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    agent = agent_name_from_env(AgentName.SUMMARIZER)
    fhir = FhirComposerOutput.model_validate(
        {key: event[key] for key in FhirComposerOutput.model_fields if key in event}
    )
    analyzer = AnalyzerOutput.model_validate(
        event.get("analyzer", {"job_id": fhir.job_id, "calls": []})
    )
    environment = os.environ.get("ENVIRONMENT", "dev")

    with track_agent_run(job_id=fhir.job_id, agent=agent):
        config = load_bedrock_config(environment)
        if not config.enabled:
            output = _stub_output(analyzer)
        else:
            bundle = _load_bundle(fhir.bundle_s3_url)
            user_prompt = build_user_prompt(
                bundle=bundle, analyzer=analyzer.model_dump(mode="json")
            )
            output = _invoke_summarizer(config.model_id, user_prompt)

        logger.info(
            "summarizer.completed",
            extra={"job_id": fhir.job_id, "confidence": output.confidence},
        )
        return {
            **output.model_dump(mode="json"),
            "job_id": fhir.job_id,
            "analyzer": analyzer.model_dump(mode="json"),
            "bundle_s3_url": fhir.bundle_s3_url,
        }
