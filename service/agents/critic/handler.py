"""Critic agent — Bedrock safety review with deterministic guardrails."""

from __future__ import annotations

import base64
import json
import os
from typing import Any
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

from service.agents.bedrock_util import invoke_claude_json, load_bedrock_config
from service.agents.critic.allowlist import deterministic_refusal_reasons
from service.agents.critic.prompts import SYSTEM_PROMPT, build_user_prompt
from service.agents.critic.schema import CriticVerdict
from service.common.dynamodb_store import AuditStore, JobsStore
from service.common.errors import PipelineError
from service.common.logging import get_logger
from service.common.models import (
    AgentName,
    AnalyzerOutput,
    AuditRecord,
    FailureReason,
    JobStatus,
    SummarizerOutput,
    utcnow,
)
from service.common.pipeline import agent_name_from_env, mark_job_succeeded, track_agent_run

logger = get_logger(__name__)

MAX_TOKENS = 256
TEMPERATURE = 0.2
CONFIDENCE_THRESHOLD = float(os.environ.get("CRITIC_CONFIDENCE_THRESHOLD", "0.6"))


def _write_audit(
    *,
    job_id: str,
    correlation_id: str,
    agent: AgentName,
    verdict: CriticVerdict,
    tokens_used: int | None,
    latency_ms: int | None,
) -> None:
    now = utcnow()
    AuditStore().put_audit(
        AuditRecord(
            job_id=job_id,
            correlation_id=correlation_id,
            agent=agent,
            event="critic_verdict",
            verdict=verdict.verdict,
            reasons=verdict.reasons,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            created_at=now,
        ),
        ttl_days=90,
    )


def _patch_bundle_with_summary(bundle_s3_url: str, summary: SummarizerOutput) -> None:
    parsed = urlparse(bundle_s3_url)
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=parsed.netloc, Key=parsed.path.lstrip("/"))
    bundle = json.loads(obj["Body"].read())
    encoded = base64.b64encode(summary.summary.encode("utf-8")).decode("ascii")
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "DocumentReference":
            resource["content"] = [
                {
                    "attachment": {
                        "contentType": "text/markdown",
                        "title": "Clinician summary",
                        "data": encoded,
                    }
                }
            ]
    s3.put_object(
        Bucket=parsed.netloc,
        Key=parsed.path.lstrip("/"),
        Body=json.dumps(bundle, separators=(",", ":")).encode("utf-8"),
        ContentType="application/fhir+json",
    )


def _correlation_id(job_id: str) -> str:
    try:
        return JobsStore().get_job(job_id).correlation_id
    except Exception:
        return job_id


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    agent = agent_name_from_env(AgentName.CRITIC)
    summary = SummarizerOutput.model_validate(
        {key: event[key] for key in SummarizerOutput.model_fields if key in event}
    )
    analyzer = AnalyzerOutput.model_validate(
        event.get("analyzer") or {"job_id": event.get("job_id", "unknown"), "calls": []}
    )
    job_id = str(event.get("job_id", analyzer.job_id))
    bundle_s3_url = str(event.get("bundle_s3_url", ""))
    environment = os.environ.get("ENVIRONMENT", "dev")
    correlation_id = _correlation_id(job_id)

    with track_agent_run(job_id=job_id, agent=agent, correlation_id=correlation_id):
        config = load_bedrock_config(environment)
        tokens_used: int | None = None
        latency_ms: int | None = None

        if not config.enabled:
            hard_reasons = deterministic_refusal_reasons(
                summary,
                analyzer,
                confidence_threshold=CONFIDENCE_THRESHOLD,
            )
            if hard_reasons:
                verdict = CriticVerdict(
                    verdict="reject",
                    reasons=hard_reasons,
                    notes="Deterministic review (Bedrock disabled).",
                )
            else:
                verdict = CriticVerdict(
                    verdict="approve",
                    reasons=[],
                    notes="Deterministic approval (Bedrock disabled).",
                )
        else:
            hard_reasons = deterministic_refusal_reasons(
                summary,
                analyzer,
                confidence_threshold=CONFIDENCE_THRESHOLD,
            )
            if hard_reasons:
                verdict = CriticVerdict(
                    verdict="reject",
                    reasons=hard_reasons,
                    notes="Deterministic guardrail triggered before Bedrock review.",
                )
            else:
                user_prompt = build_user_prompt(
                    summary=summary.model_dump(mode="json"),
                    analyzer=analyzer.model_dump(mode="json"),
                )
                result = invoke_claude_json(
                    model_id=config.model_id,
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                )
                tokens_used = result.tokens_used
                latency_ms = result.latency_ms
                try:
                    verdict = CriticVerdict.model_validate(result.payload)
                except Exception as err:
                    raise PipelineError(
                        FailureReason.INVALID_LLM_OUTPUT,
                        "critic output failed schema validation",
                        cause=err,
                    ) from err
                post_reasons = deterministic_refusal_reasons(
                    summary,
                    analyzer,
                    confidence_threshold=CONFIDENCE_THRESHOLD,
                )
                if post_reasons:
                    verdict = CriticVerdict(
                        verdict="reject",
                        reasons=post_reasons,
                        notes="Deterministic guardrail triggered after Bedrock review.",
                    )

        _write_audit(
            job_id=job_id,
            correlation_id=correlation_id,
            agent=agent,
            verdict=verdict,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )

        if verdict.verdict == "approve":
            if bundle_s3_url:
                try:
                    _patch_bundle_with_summary(bundle_s3_url, summary)
                except ClientError as err:
                    raise PipelineError(
                        FailureReason.S3_WRITE_FAILED,
                        "failed to patch FHIR bundle with summary",
                        cause=err,
                    ) from err
            mark_job_succeeded(job_id)
        else:
            JobsStore().update_job(
                job_id,
                status=JobStatus.FAILED,
                failure_reason=verdict.reasons[0].value
                if verdict.reasons
                else FailureReason.LOW_CONFIDENCE.value,
                clear_current_step=True,
            )

        logger.info(
            "critic.completed",
            extra={"job_id": job_id, "verdict": verdict.verdict, "correlation_id": correlation_id},
        )
        return verdict.model_dump(mode="json")
