"""FHIR Composer agent — write Bundle JSON to S3."""

from __future__ import annotations

import json
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

from service.agents.fhir_composer.fhir_models import build_bundle
from service.common.errors import PipelineError
from service.common.logging import get_logger
from service.common.models import AgentName, AnalyzerOutput, FailureReason, FhirComposerOutput
from service.common.pipeline import agent_name_from_env, mark_job_succeeded, track_agent_run

logger = get_logger(__name__)


def _write_bundle(job_id: str, bundle: dict[str, Any]) -> str:
    bucket = os.environ.get("REPORTS_BUCKET", "")
    if not bucket:
        raise PipelineError(FailureReason.S3_WRITE_FAILED, "REPORTS_BUCKET is not configured")
    key = f"{job_id}/bundle.json"
    body = json.dumps(bundle, separators=(",", ":")).encode("utf-8")
    try:
        boto3.client("s3").put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/fhir+json",
        )
    except ClientError as err:
        raise PipelineError(
            FailureReason.S3_WRITE_FAILED,
            "failed to write FHIR bundle to S3",
            cause=err,
        ) from err
    return f"s3://{bucket}/{key}"


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    agent = agent_name_from_env(AgentName.FHIR_COMPOSER)
    try:
        analyzer = AnalyzerOutput.model_validate(event)
    except Exception as err:
        raise PipelineError(
            FailureReason.INVALID_FHIR_PAYLOAD,
            "invalid analyzer payload for fhir composer",
            cause=err,
        ) from err

    with track_agent_run(job_id=analyzer.job_id, agent=agent):
        built = build_bundle(analyzer)
        bundle_url = _write_bundle(analyzer.job_id, built["bundle"])
        output = FhirComposerOutput(
            job_id=analyzer.job_id,
            bundle_s3_url=bundle_url,
            resource_counts=built["resource_counts"],
        )
        mark_job_succeeded(analyzer.job_id)
        logger.info(
            "fhir_composer.completed",
            extra={"job_id": analyzer.job_id, "bundle_s3_url": bundle_url},
        )
        return output.model_dump(mode="json")
