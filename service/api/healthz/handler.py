"""GET /healthz — liveness probe for the API and synthetic canary."""

from __future__ import annotations

import os
from typing import Any

from service.common.api_gateway import json_response
from service.common.errors import ServiceError, to_api_response
from service.common.logging import get_logger

logger = get_logger(__name__)


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    try:
        body = {
            "status": "ok",
            "version": os.environ.get("VERSION", "0.0.0"),
            "env": os.environ.get("ENVIRONMENT", "unknown"),
        }
        logger.info("healthz.ok", extra={"env": body["env"]})
        return json_response(200, body)
    except ServiceError as err:
        return to_api_response(err)
    except Exception as err:
        return to_api_response(ServiceError.internal(err))
