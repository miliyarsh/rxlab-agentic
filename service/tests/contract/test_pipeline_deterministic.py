"""Contract test for the deterministic 3-agent pipeline against deployed dev."""

from __future__ import annotations

import json
import os
import time
import urllib.request

import pytest


def _api_url() -> str | None:
    return os.environ.get("API_URL")


@pytest.mark.contract
def test_pipeline_deterministic_e2e() -> None:
    api_url = _api_url()
    if not api_url:
        pytest.skip("API_URL is not set; deploy dev and export API_URL to run contract tests")

    base = api_url.rstrip("/")
    submit_body = json.dumps(
        {
            "sample_id": "S-contract-001",
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
        assert resp.status == 202
        payload = json.loads(resp.read())
    job_id = payload["job_id"]

    deadline = time.time() + float(os.environ.get("CONTRACT_TIMEOUT_SECONDS", "120"))
    status = "pending"
    while time.time() < deadline:
        with urllib.request.urlopen(f"{base}/jobs/{job_id}", timeout=15) as resp:
            job = json.loads(resp.read())
        status = job["status"]
        if status in {"succeeded", "failed"}:
            break
        time.sleep(3)

    assert status == "succeeded", f"job {job_id} ended with status={status}"

    with urllib.request.urlopen(f"{base}/jobs/{job_id}/report", timeout=15) as resp:
        report = json.loads(resp.read())
    assert "presigned_url" in report

    with urllib.request.urlopen(report["presigned_url"], timeout=30) as bundle_resp:
        bundle = json.loads(bundle_resp.read())

    resource_types = {entry["resource"]["resourceType"] for entry in bundle["entry"]}
    assert "Observation" in resource_types
    assert "MedicationStatement" in resource_types
