"""POST /jobs — validate request, persist job row, start Step Functions execution."""

from __future__ import annotations

import os
import uuid
from typing import Any

import boto3
from botocore.exceptions import ClientError
from pydantic import ValidationError as PydanticValidationError

from service.common.api_gateway import (
    json_response,
    parse_json_body,
    validation_error_from_pydantic,
)
from service.common.dynamodb_store import JobsStore
from service.common.errors import ServiceError, UpstreamError, to_api_response
from service.common.logging import get_logger
from service.common.models import (
    JobRecord,
    JobStatus,
    PipelineEvent,
    SubmitJobRequest,
    SubmitJobResponse,
    utcnow,
)

logger = get_logger(__name__)


def _new_job_id() -> str:
    return f"j_{uuid.uuid4().hex}"


def _correlation_id(event: dict[str, Any]) -> str:
    headers = event.get("headers") or {}
    for key, value in headers.items():
        if key.lower() == "x-correlation-id" and value:
            return str(value)
    return str(uuid.uuid4())


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    try:
        body = parse_json_body(event)
        try:
            request = SubmitJobRequest.model_validate(body)
        except PydanticValidationError as err:
            raise validation_error_from_pydantic(err) from err

        job_id = _new_job_id()
        correlation_id = _correlation_id(event)
        now = utcnow()

        record = JobRecord(
            job_id=job_id,
            sample_id=request.sample_id,
            status=JobStatus.PENDING,
            correlation_id=correlation_id,
            vcf_url=request.vcf_url,
            report_ready=False,
            created_at=now,
            updated_at=now,
        )
        JobsStore().put_job(record)

        pipeline_input = PipelineEvent(
            job_id=job_id,
            sample_id=request.sample_id,
            vcf_url=request.vcf_url,
            correlation_id=correlation_id,
        )

        state_machine_arn = os.environ.get("STATE_MACHINE_ARN", "")
        if not state_machine_arn:
            raise UpstreamError("STATE_MACHINE_ARN is not configured")

        sfn = boto3.client("stepfunctions")
        try:
            sfn.start_execution(
                stateMachineArn=state_machine_arn,
                name=f"{job_id}-{uuid.uuid4().hex[:8]}",
                input=pipeline_input.model_dump_json(),
            )
        except ClientError as err:
            raise UpstreamError("failed to start pipeline execution", cause=err) from err

        logger.info(
            "submit_job.accepted",
            extra={
                "job_id": job_id,
                "correlation_id": correlation_id,
                "sample_id": request.sample_id,
            },
        )

        response = SubmitJobResponse(job_id=job_id, status="pending")
        return json_response(202, response.model_dump())
    except ServiceError as err:
        return to_api_response(err)
    except Exception as err:
        logger.exception("submit_job.unhandled", extra={"error_class": type(err).__name__})
        return to_api_response(ServiceError.internal(err))
