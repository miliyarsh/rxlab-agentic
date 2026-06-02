"""Unit tests for Summarizer agent."""

from __future__ import annotations

import json
from typing import Any

import boto3
import pytest

from service.agents.summarizer.handler import handler
from service.common.models import AnalyzerCall, AnalyzerOutput, CpicRecommendation


@pytest.mark.unit
def test_summarizer_stub_when_bedrock_disabled(
    moto_env: None,
    aws_region: str,
    jobs_table: str,
    agent_runs_table: str,
    reports_bucket: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JOBS_TABLE", jobs_table)
    monkeypatch.setenv("AGENT_RUNS_TABLE", agent_runs_table)
    monkeypatch.setenv("AUDIT_TABLE", "rxlab-audit-test")
    monkeypatch.setenv("AGENT_NAME", "summarizer")
    monkeypatch.setenv("BEDROCK_ENABLED", "false")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-haiku-4-5-20251001-v1:0")

    boto3.client("dynamodb", region_name=aws_region).create_table(
        TableName="rxlab-audit-test",
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

    bundle_key = "j_sum1/bundle.json"
    boto3.client("s3", region_name=aws_region).put_object(
        Bucket=reports_bucket,
        Key=bundle_key,
        Body=json.dumps({"resourceType": "Bundle", "entry": []}).encode(),
    )

    from service.tests.conftest import seed_job

    seed_job("j_sum1")

    analyzer = AnalyzerOutput(
        job_id="j_sum1",
        calls=[
            AnalyzerCall(
                gene="CYP2C19",
                genotype="*1/*2",
                phenotype="Intermediate Metabolizer",
                cpic_recommendations=[
                    CpicRecommendation(
                        drug="clopidogrel",
                        recommendation="Consider alternative antiplatelet therapy",
                        citation="CPIC: Clopidogrel and CYP2C19 — 2022 update",
                    )
                ],
            )
        ],
    )

    event: dict[str, Any] = {
        "job_id": "j_sum1",
        "bundle_s3_url": f"s3://{reports_bucket}/{bundle_key}",
        "resource_counts": {"Observation": 1},
        "analyzer": analyzer.model_dump(mode="json"),
    }

    result = handler(event, None)
    assert result["confidence"] == 0.85
    assert result["citations"]
