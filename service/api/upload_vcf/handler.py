"""POST /uploads/vcf — accept a VCF upload and store it in the reports bucket."""

from __future__ import annotations

import base64
import binascii
import os
import re
import uuid
from typing import Any

from botocore.exceptions import ClientError
from pydantic import ValidationError as PydanticValidationError

from service.common.api_gateway import (
    json_response,
    parse_json_body,
    validation_error_from_pydantic,
)
from service.common.errors import ServiceError, UpstreamError, ValidationError, to_api_response
from service.common.logging import get_logger
from service.common.models import UploadVcfRequest, UploadVcfResponse
from service.common.s3_client import s3_client

logger = get_logger(__name__)

_MAX_VCF_BYTES = 5 * 1024 * 1024
_VCF_HEADER_PATTERN = re.compile(r"^##fileformat=|^#CHROM\t", re.MULTILINE)


def _decode_vcf(content_base64: str) -> bytes:
    try:
        raw = base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError) as err:
        raise ValidationError("content_base64 must be valid base64", cause=err) from err
    if len(raw) == 0:
        raise ValidationError("uploaded VCF is empty")
    if len(raw) > _MAX_VCF_BYTES:
        raise ValidationError(f"uploaded VCF exceeds {_MAX_VCF_BYTES // (1024 * 1024)} MB limit")
    return raw


def _validate_vcf_bytes(raw: bytes) -> None:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as err:
        raise ValidationError("uploaded VCF must be UTF-8 text", cause=err) from err
    if not _VCF_HEADER_PATTERN.search(text):
        raise ValidationError(
            "uploaded file does not look like a VCF (missing ##fileformat or #CHROM header)"
        )


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    try:
        body = parse_json_body(event)
        try:
            request = UploadVcfRequest.model_validate(body)
        except PydanticValidationError as err:
            raise validation_error_from_pydantic(err) from err

        bucket = os.environ.get("REPORTS_BUCKET", "")
        if not bucket:
            raise UpstreamError("REPORTS_BUCKET is not configured")

        raw = _decode_vcf(request.content_base64)
        _validate_vcf_bytes(raw)

        upload_id = uuid.uuid4().hex
        key = f"uploads/{upload_id}/{request.filename}"
        vcf_url = f"s3://{bucket}/{key}"

        s3 = s3_client()
        try:
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=raw,
                ContentType="text/plain",
                Metadata={"original-filename": request.filename},
            )
        except ClientError as err:
            raise UpstreamError("failed to store uploaded VCF", cause=err) from err

        response = UploadVcfResponse(vcf_url=vcf_url, object_key=key)
        logger.info("upload_vcf.ok", extra={"object_key": key, "bytes": len(raw)})
        return json_response(201, response.model_dump())
    except ServiceError as err:
        return to_api_response(err)
    except Exception as err:
        logger.exception("upload_vcf.unhandled", extra={"error_class": type(err).__name__})
        return to_api_response(ServiceError.internal(err))
