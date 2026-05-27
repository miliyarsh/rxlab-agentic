"""Unit tests for Intake VCF parsing and handler."""

from __future__ import annotations

from pathlib import Path

import boto3
import pytest

from service.agents.intake.handler import handler as intake_handler
from service.agents.intake.vcf_parser import parse_vcf_text
from service.common.errors import PipelineError
from service.common.models import FailureReason
from service.tests.conftest import seed_job

FIXTURE = Path(__file__).resolve().parents[2] / "agents" / "intake" / "fixtures" / "sample.vcf"


@pytest.mark.unit
def test_parse_sample_vcf() -> None:
    parsed = parse_vcf_text(FIXTURE.read_text(encoding="utf-8"))
    assert parsed.sample_class in {"exome", "panel", "other"}
    assert len(parsed.variants) == 2
    genes = {v.gene for v in parsed.variants}
    assert "CYP2C19" in genes
    assert "TPMT" in genes


@pytest.mark.unit
def test_parse_empty_vcf_raises() -> None:
    with pytest.raises(PipelineError) as exc:
        parse_vcf_text("")
    assert exc.value.reason == FailureReason.EMPTY_VCF


@pytest.mark.integration
def test_intake_handler_reads_s3(
    moto_env: None,
    aws_region: str,
    jobs_table: str,
    agent_runs_table: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bucket = "rxlab-intake-test"
    boto3.client("s3", region_name=aws_region).create_bucket(Bucket=bucket)
    key = "samples/sample.vcf"
    boto3.client("s3", region_name=aws_region).put_object(
        Bucket=bucket,
        Key=key,
        Body=FIXTURE.read_bytes(),
    )
    monkeypatch.setenv("JOBS_TABLE", jobs_table)
    monkeypatch.setenv("AGENT_RUNS_TABLE", agent_runs_table)
    monkeypatch.setenv("AGENT_NAME", "intake")
    monkeypatch.setenv("REPORTS_BUCKET", bucket)

    seed_job("j_intake1", vcf_url=f"s3://{bucket}/{key}", correlation_id="corr-1")

    event = {
        "job_id": "j_intake1",
        "sample_id": "S-001",
        "vcf_url": f"s3://{bucket}/{key}",
        "correlation_id": "corr-1",
    }
    result = intake_handler(event, None)
    assert result["job_id"] == "j_intake1"
    assert len(result["variants"]) == 2
