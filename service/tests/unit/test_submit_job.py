"""Unit tests for POST /jobs handler."""

from __future__ import annotations

import json
from typing import Any

import pytest

from service.api.submit_job.handler import handler


@pytest.mark.unit
def test_submit_job_validation_error(api_env: dict[str, str]) -> None:
    event: dict[str, Any] = {
        "body": json.dumps({"sample_id": "", "vcf_url": "not-s3"}),
        "headers": {},
    }
    response = handler(event, None)
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"]["code"] == "VALIDATION_ERROR"
