"""Integration test — full 5-agent handler chain in-process (moto, Bedrock disabled)."""

from __future__ import annotations

from pathlib import Path

import boto3
import pytest

from service.agents.analyzer.handler import handler as analyzer_handler
from service.agents.critic.handler import handler as critic_handler
from service.agents.fhir_composer.handler import handler as fhir_handler
from service.agents.intake.handler import handler as intake_handler
from service.agents.summarizer.handler import handler as summarizer_handler
from service.common.dynamodb_store import JobsStore
from service.common.models import JobStatus, PipelineEvent
from service.tests.conftest import seed_job


@pytest.fixture
def pipeline_env(
    monkeypatch: pytest.MonkeyPatch,
    jobs_table: str,
    agent_runs_table: str,
    reports_bucket: str,
    aws_region: str,
) -> str:
    audit_table = "rxlab-audit-pipeline-test"
    monkeypatch.setenv("JOBS_TABLE", jobs_table)
    monkeypatch.setenv("AGENT_RUNS_TABLE", agent_runs_table)
    monkeypatch.setenv("AUDIT_TABLE", audit_table)
    monkeypatch.setenv("REPORTS_BUCKET", reports_bucket)
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("BEDROCK_ENABLED", "false")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-haiku-4-5-20251001-v1:0")

    boto3.client("dynamodb", region_name=aws_region).create_table(
        TableName=audit_table,
        AttributeDefinitions=[
            {"AttributeName": "job_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "job_id", "KeyType": "HASH"},
            {"AttributeName": "created_at", "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    fixture = Path(__file__).resolve().parents[2] / "agents" / "intake" / "fixtures" / "sample.vcf"
    key = "samples/sample.vcf"
    boto3.client("s3", region_name=aws_region).put_object(
        Bucket=reports_bucket,
        Key=key,
        Body=fixture.read_bytes(),
    )
    return f"s3://{reports_bucket}/{key}"


@pytest.mark.integration
def test_pipeline_five_agent_happy_path(pipeline_env: str) -> None:
    job_id = "j_pipeline_happy"
    vcf_url = pipeline_env
    seed_job(job_id, vcf_url=vcf_url)

    intake_out = intake_handler(
        PipelineEvent(
            job_id=job_id,
            sample_id="S-pipeline",
            vcf_url=vcf_url,
            correlation_id="corr-pipeline",
        ).model_dump(mode="json"),
        None,
    )
    analyzer_out = analyzer_handler(intake_out, None)
    fhir_out = fhir_handler(analyzer_out, None)
    summary_out = summarizer_handler(fhir_out, None)
    verdict = critic_handler(summary_out, None)

    assert verdict["verdict"] == "approve"
    job = JobsStore().get_job(job_id)
    assert job.status == JobStatus.SUCCEEDED
    assert job.report_ready is True


@pytest.mark.integration
def test_pipeline_critic_refusal_low_confidence(
    pipeline_env: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = "j_pipeline_refuse"
    vcf_url = pipeline_env
    seed_job(job_id, vcf_url=vcf_url)

    intake_out = intake_handler(
        PipelineEvent(
            job_id=job_id,
            sample_id="S-refuse",
            vcf_url=vcf_url,
            correlation_id="corr-refuse",
        ).model_dump(mode="json"),
        None,
    )
    analyzer_out = analyzer_handler(intake_out, None)
    fhir_out = fhir_handler(analyzer_out, None)
    summary_out = summarizer_handler(fhir_out, None)
    summary_out["confidence"] = 0.2
    verdict = critic_handler(summary_out, None)

    assert verdict["verdict"] == "reject"
    assert "low_confidence" in verdict["reasons"]
    job = JobsStore().get_job(job_id)
    assert job.status == JobStatus.FAILED
