"""Contract tests for the full 5-agent pipeline against deployed dev."""

from __future__ import annotations

import json
import os
import time
import urllib.request

import pytest


def _api_url() -> str | None:
    return os.environ.get("API_URL")


@pytest.mark.contract
def test_pipeline_full_happy_path() -> None:
    api_url = _api_url()
    if not api_url:
        pytest.skip("API_URL is not set")

    base = api_url.rstrip("/")
    submit_body = json.dumps(
        {
            "sample_id": "S-full-001",
            "vcf_url": os.environ.get(
                "CONTRACT_VCF_URL",
                "s3://rxlab-reports-dev-PLACEHOLDER/samples/sample.vcf",
            ),
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/jobs",
        data=submit_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read())
    job_id = payload["job_id"]

    deadline = time.time() + float(os.environ.get("CONTRACT_TIMEOUT_SECONDS", "180"))
    status = "pending"
    while time.time() < deadline:
        with urllib.request.urlopen(f"{base}/jobs/{job_id}", timeout=15) as resp:
            job = json.loads(resp.read())
        status = job["status"]
        if status in {"succeeded", "failed"}:
            break
        time.sleep(5)

    assert status == "succeeded", f"expected succeeded, got {status}"


@pytest.mark.contract
def test_pipeline_refusal_is_clean_failure() -> None:
    pytest.skip(
        "Critic refusal path is covered by service/tests/integration/test_pipeline_handlers.py"
    )
