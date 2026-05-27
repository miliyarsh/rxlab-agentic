"""Integration tests for API handlers using moto."""

from __future__ import annotations

import json
from typing import Any

import boto3
import pytest

from service.api.get_job.handler import handler as get_job_handler
from service.api.get_report.handler import handler as get_report_handler
from service.api.healthz.handler import handler as healthz_handler
from service.api.submit_job.handler import handler as submit_job_handler
from service.common.dynamodb_store import JobsStore
from service.common.models import JobRecord, JobStatus, utcnow


@pytest.mark.integration
def test_submit_and_get_job(api_env: dict[str, str], reports_bucket: str) -> None:
    vcf_key = "samples/sample.vcf"
    boto3.client("s3").put_object(
        Bucket=reports_bucket,
        Key=vcf_key,
        Body=b"##fileformat=VCFv4.2\n",
    )
    submit_event: dict[str, Any] = {
        "body": json.dumps(
            {
                "sample_id": "S-001",
                "vcf_url": f"s3://{reports_bucket}/{vcf_key}",
            }
        ),
        "headers": {"x-correlation-id": "corr-123"},
    }
    submit_resp = submit_job_handler(submit_event, None)
    assert submit_resp["statusCode"] == 202
    job_id = json.loads(submit_resp["body"])["job_id"]

    get_resp = get_job_handler({"pathParameters": {"id": job_id}}, None)
    assert get_resp["statusCode"] == 200
    payload = json.loads(get_resp["body"])
    assert payload["job_id"] == job_id
    assert payload["status"] == "pending"


@pytest.mark.integration
def test_get_report_not_ready(api_env: dict[str, str]) -> None:
    job_id = "j_test123"
    now = utcnow()
    JobsStore().put_job(
        JobRecord(
            job_id=job_id,
            sample_id="S-1",
            status=JobStatus.RUNNING,
            correlation_id="c-1",
            vcf_url="s3://bucket/sample.vcf",
            report_ready=False,
            created_at=now,
            updated_at=now,
        )
    )
    resp = get_report_handler({"pathParameters": {"id": job_id}}, None)
    assert resp["statusCode"] == 409


@pytest.mark.integration
def test_healthz(api_env: dict[str, str]) -> None:
    resp = healthz_handler({}, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["status"] == "ok"
    assert body["env"] == "test"
