"""Shared pytest fixtures for moto-backed integration tests."""

from __future__ import annotations

from collections.abc import Generator

import boto3
import pytest
from moto import mock_aws

from service.common.dynamodb_store import JobsStore
from service.common.models import JobRecord, JobStatus, utcnow


def seed_job(
    job_id: str,
    *,
    sample_id: str = "S-test",
    status: JobStatus = JobStatus.PENDING,
    correlation_id: str = "corr-test",
    vcf_url: str = "s3://bucket/sample.vcf",
) -> JobRecord:
    now = utcnow()
    record = JobRecord(
        job_id=job_id,
        sample_id=sample_id,
        status=status,
        correlation_id=correlation_id,
        vcf_url=vcf_url,
        report_ready=False,
        created_at=now,
        updated_at=now,
    )
    JobsStore().put_job(record)
    return record


@pytest.fixture
def aws_region() -> str:
    return "us-east-1"


@pytest.fixture
def moto_env(aws_region: str, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AWS_DEFAULT_REGION", aws_region)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    with mock_aws():
        yield


@pytest.fixture
def jobs_table(moto_env: None, aws_region: str) -> str:
    name = "rxlab-jobs-test"
    client = boto3.client("dynamodb", region_name=aws_region)
    client.create_table(
        TableName=name,
        AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
        BillingMode="PAY_PER_REQUEST",
    )
    return name


@pytest.fixture
def agent_runs_table(moto_env: None, aws_region: str) -> str:
    name = "rxlab-agent-runs-test"
    client = boto3.client("dynamodb", region_name=aws_region)
    client.create_table(
        TableName=name,
        AttributeDefinitions=[
            {"AttributeName": "job_id", "AttributeType": "S"},
            {"AttributeName": "agent", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "job_id", "KeyType": "HASH"},
            {"AttributeName": "agent", "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    return name


@pytest.fixture
def reports_bucket(moto_env: None, aws_region: str) -> str:
    name = "rxlab-reports-test"
    boto3.client("s3", region_name=aws_region).create_bucket(Bucket=name)
    return name


@pytest.fixture
def state_machine_arn(moto_env: None, aws_region: str) -> str:
    client = boto3.client("stepfunctions", region_name=aws_region)
    role = boto3.client("iam").create_role(
        RoleName="sfn-test-role",
        AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[]}',
    )
    arn = client.create_state_machine(
        name="rxlab-test-pipeline",
        definition='{"StartAt":"Done","States":{"Done":{"Type":"Succeed"}}}',
        roleArn=role["Role"]["Arn"],
    )["stateMachineArn"]
    return arn


@pytest.fixture
def api_env(
    monkeypatch: pytest.MonkeyPatch,
    jobs_table: str,
    agent_runs_table: str,
    reports_bucket: str,
    state_machine_arn: str,
) -> dict[str, str]:
    env = {
        "JOBS_TABLE": jobs_table,
        "AGENT_RUNS_TABLE": agent_runs_table,
        "REPORTS_BUCKET": reports_bucket,
        "STATE_MACHINE_ARN": state_machine_arn,
        "ENVIRONMENT": "test",
        "VERSION": "0.1.0-test",
        "PRESIGNED_URL_TTL": "900",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return env
