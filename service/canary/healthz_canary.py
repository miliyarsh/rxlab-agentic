"""Scheduled healthz canary — probes API_URL and emits a CloudWatch metric."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

import boto3

from service.common.logging import get_logger

logger = get_logger(__name__)

METRIC_NAMESPACE = "RxLab/Canary"


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    api_url = os.environ.get("API_URL", "").rstrip("/")
    if not api_url:
        logger.error("canary.misconfigured", extra={"reason": "API_URL missing"})
        _emit_metric(success=0.0)
        return {"status": "error", "reason": "API_URL missing"}

    success = 0.0
    try:
        req = urllib.request.Request(f"{api_url}/healthz", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
            body = json.loads(resp.read())
            if resp.status == 200 and body.get("status") == "ok":
                success = 1.0
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
        logger.warning("canary.probe_failed", extra={"error_class": type(err).__name__})

    _emit_metric(success=success)
    logger.info("canary.completed", extra={"success": success})
    return {"status": "ok" if success else "fail", "success": success}


def _emit_metric(*, success: float) -> None:
    boto3.client("cloudwatch").put_metric_data(
        Namespace=METRIC_NAMESPACE,
        MetricData=[{"MetricName": "HealthzSuccess", "Value": success, "Unit": "Count"}],
    )
