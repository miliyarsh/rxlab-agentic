"""Integration tests for API handlers using moto."""

from __future__ import annotations

import base64
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
def test_get_report_bundle_inline(api_env: dict[str, str], reports_bucket: str) -> None:
    job_id = "j_bundle123"
    now = utcnow()
    JobsStore().put_job(
        JobRecord(
            job_id=job_id,
            sample_id="S-1",
            status=JobStatus.SUCCEEDED,
            correlation_id="c-1",
            vcf_url="s3://bucket/sample.vcf",
            report_ready=True,
            created_at=now,
            updated_at=now,
        )
    )
    bundle = {"resourceType": "Bundle", "type": "collection", "entry": []}
    boto3.client("s3").put_object(
        Bucket=reports_bucket,
        Key=f"{job_id}/bundle.json",
        Body=json.dumps(bundle).encode("utf-8"),
        ContentType="application/json",
    )

    resp = get_report_handler(
        {"pathParameters": {"id": job_id}, "queryStringParameters": {"include": "bundle"}},
        None,
    )
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"]) == bundle


@pytest.mark.integration
def test_get_report_presigned_url_uses_sigv4(api_env: dict[str, str], reports_bucket: str) -> None:
    job_id = "j_presign123"
    now = utcnow()
    JobsStore().put_job(
        JobRecord(
            job_id=job_id,
            sample_id="S-1",
            status=JobStatus.SUCCEEDED,
            correlation_id="c-1",
            vcf_url="s3://bucket/sample.vcf",
            report_ready=True,
            created_at=now,
            updated_at=now,
        )
    )
    boto3.client("s3").put_object(
        Bucket=reports_bucket,
        Key=f"{job_id}/bundle.json",
        Body=b'{"resourceType":"Bundle"}',
        ContentType="application/json",
    )

    resp = get_report_handler({"pathParameters": {"id": job_id}}, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "presigned_url" in body
    assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in body["presigned_url"]


@pytest.mark.integration
def test_upload_vcf(api_env: dict[str, str], reports_bucket: str) -> None:
    from service.api.upload_vcf.handler import handler as upload_vcf_handler

    vcf_text = "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\n10\t96541616\t.\tG\tA\n"
    payload = {
        "filename": "upload-test.vcf",
        "content_base64": base64.b64encode(vcf_text.encode("utf-8")).decode("ascii"),
    }
    resp = upload_vcf_handler({"body": json.dumps(payload)}, None)
    assert resp["statusCode"] == 201
    body = json.loads(resp["body"])
    assert body["vcf_url"].startswith(f"s3://{reports_bucket}/uploads/")
    assert body["object_key"].endswith("upload-test.vcf")

    obj = boto3.client("s3").get_object(Bucket=reports_bucket, Key=body["object_key"])
    assert obj["Body"].read().decode("utf-8") == vcf_text


@pytest.mark.integration
def test_healthz(api_env: dict[str, str]) -> None:
    resp = healthz_handler({}, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["status"] == "ok"
    assert body["env"] == "test"
