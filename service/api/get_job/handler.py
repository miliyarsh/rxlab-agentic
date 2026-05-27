"""GET /jobs/{id} — return the current job status from DynamoDB."""

from __future__ import annotations

from typing import Any

from service.common.api_gateway import json_response, path_parameter
from service.common.dynamodb_store import JobsStore
from service.common.errors import ServiceError, to_api_response
from service.common.logging import get_logger
from service.common.models import GetJobResponse

logger = get_logger(__name__)


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    try:
        job_id = path_parameter(event, "id")
        record = JobsStore().get_job(job_id)
        response = GetJobResponse(
            job_id=record.job_id,
            status=record.status,
            current_step=record.current_step,
            report_ready=record.report_ready,
            failure_reason=record.failure_reason,
        )
        logger.info("get_job.ok", extra={"job_id": job_id, "status": record.status.value})
        return json_response(200, response.model_dump(mode="json"))
    except ServiceError as err:
        return to_api_response(err)
    except Exception as err:
        logger.exception("get_job.unhandled", extra={"error_class": type(err).__name__})
        return to_api_response(ServiceError.internal(err))
