"""Intake agent — validate VCF from S3 and emit structured variants."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

from service.agents.intake.vcf_parser import parse_vcf_text
from service.common.errors import PipelineError
from service.common.logging import get_logger
from service.common.models import AgentName, FailureReason, IntakeOutput, PipelineEvent
from service.common.pipeline import agent_name_from_env, track_agent_run

logger = get_logger(__name__)


def _read_vcf_from_s3(vcf_url: str) -> str:
    parsed = urlparse(vcf_url)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path.lstrip("/"):
        raise PipelineError(FailureReason.INVALID_VCF_SCHEMA, "vcf_url must be an s3:// URL")
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    try:
        obj = boto3.client("s3").get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read()
    except ClientError as err:
        raise PipelineError(
            FailureReason.UNREACHABLE_VCF,
            "unable to read VCF object",
            cause=err,
        ) from err
    return body.decode("utf-8")


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    agent = agent_name_from_env(AgentName.INTAKE)
    try:
        pipeline = PipelineEvent.model_validate(event)
    except Exception as err:
        raise PipelineError(
            FailureReason.INVALID_VCF_SCHEMA,
            "invalid pipeline event payload",
            cause=err,
        ) from err

    with track_agent_run(
        job_id=pipeline.job_id,
        agent=agent,
        correlation_id=pipeline.correlation_id,
    ):
        content = _read_vcf_from_s3(pipeline.vcf_url)
        parsed = parse_vcf_text(content)
        output = IntakeOutput(
            job_id=pipeline.job_id,
            sample_id=pipeline.sample_id,
            sample_class=parsed.sample_class,  # type: ignore[arg-type]
            variants=parsed.variants,
            warnings=parsed.warnings,
        )
        logger.info(
            "intake.completed",
            extra={
                "job_id": pipeline.job_id,
                "variant_count": len(output.variants),
                "correlation_id": pipeline.correlation_id,
            },
        )
        return output.model_dump(mode="json")
