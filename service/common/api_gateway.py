"""HTTP API Gateway v2 event helpers for API Lambda handlers."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from service.common.errors import ValidationError


def json_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body, separators=(",", ":")),
    }


def parse_json_body(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("body")
    if raw is None or raw == "":
        raise ValidationError("request body is required")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as err:
        raise ValidationError("request body must be valid JSON", cause=err) from err
    if not isinstance(parsed, dict):
        raise ValidationError("request body must be a JSON object")
    return parsed


def path_parameter(event: dict[str, Any], name: str) -> str:
    params = event.get("pathParameters") or {}
    value = params.get(name)
    if value is None or value == "":
        raise ValidationError(f"path parameter '{name}' is required")
    return str(value)


def header_value(event: dict[str, Any], name: str) -> str | None:
    headers = event.get("headers") or {}
    for key, value in headers.items():
        if key.lower() == name.lower():
            return str(value)
    return None


def validation_error_from_pydantic(err: PydanticValidationError) -> ValidationError:
    return ValidationError(
        "request validation failed",
        details={"errors": err.errors(include_url=False)},
        cause=err,
    )
