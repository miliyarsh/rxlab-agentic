"""GET /jobs/{id}/report — presigned URL or inline FHIR bundle (``?include=bundle``)."""

from __future__ import annotations

import json
import os
from typing import Any

from botocore.exceptions import ClientError

from service.common.api_gateway import json_response, path_parameter, query_parameter
from service.common.dynamodb_store import JobsStore
from service.common.errors import JobNotReadyError, ServiceError, UpstreamError, to_api_response
from service.common.logging import get_logger
from service.common.models import GetReportResponse
from service.common.s3_client import s3_client

logger = get_logger(__name__)


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    try:
        job_id = path_parameter(event, "id")
        record = JobsStore().get_job(job_id)
        if not record.report_ready:
            raise JobNotReadyError(f"report for job '{job_id}' is not ready yet")

        bucket = os.environ.get("REPORTS_BUCKET", "")
        if not bucket:
            raise UpstreamError("REPORTS_BUCKET is not configured")

        ttl = int(os.environ.get("PRESIGNED_URL_TTL", "900"))
        key = f"{job_id}/bundle.json"
        s3 = s3_client()

        if query_parameter(event, "include") == "bundle":
            try:
                obj = s3.get_object(Bucket=bucket, Key=key)
                bundle = json.loads(obj["Body"].read())
            except ClientError as err:
                raise UpstreamError("failed to read report bundle", cause=err) from err
            except json.JSONDecodeError as err:
                raise UpstreamError("report bundle is not valid JSON", cause=err) from err
            if not isinstance(bundle, dict):
                raise UpstreamError("report bundle must be a JSON object")
            logger.info("get_report.bundle_ok", extra={"job_id": job_id})
            return json_response(200, bundle)

        try:
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=ttl,
            )
        except ClientError as err:
            raise UpstreamError("failed to generate presigned URL", cause=err) from err

        response = GetReportResponse(presigned_url=url, expires_in_seconds=ttl)
        logger.info("get_report.ok", extra={"job_id": job_id})
        return json_response(200, response.model_dump())
    except ServiceError as err:
        return to_api_response(err)
    except Exception as err:
        logger.exception("get_report.unhandled", extra={"error_class": type(err).__name__})
        return to_api_response(ServiceError.internal(err))
