"""Unit tests for Critic agent."""

from __future__ import annotations

import json

import boto3
import pytest

from service.agents.critic.handler import handler
from service.common.models import (
    AnalyzerCall,
    AnalyzerOutput,
    CpicRecommendation,
    SummarizerCitation,
    SummarizerFinding,
    SummarizerOutput,
)
from service.tests.conftest import seed_job


@pytest.mark.unit
def test_critic_rejects_low_confidence_when_bedrock_disabled(
    moto_env: None,
    aws_region: str,
    jobs_table: str,
    agent_runs_table: str,
    reports_bucket: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_table = "rxlab-audit-test"
    monkeypatch.setenv("JOBS_TABLE", jobs_table)
    monkeypatch.setenv("AGENT_RUNS_TABLE", agent_runs_table)
    monkeypatch.setenv("AUDIT_TABLE", audit_table)
    monkeypatch.setenv("AGENT_NAME", "critic")
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

    seed_job("j_crit1")
    bundle_key = "j_crit1/bundle.json"
    boto3.client("s3", region_name=aws_region).put_object(
        Bucket=reports_bucket,
        Key=bundle_key,
        Body=json.dumps(
            {
                "resourceType": "Bundle",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "DocumentReference",
                            "content": [{"attachment": {"title": "placeholder"}}],
                        }
                    }
                ],
            }
        ).encode(),
    )

    analyzer = AnalyzerOutput(
        job_id="j_crit1",
        calls=[
            AnalyzerCall(
                gene="CYP2C19",
                genotype="*1/*2",
                phenotype="Intermediate Metabolizer",
                cpic_recommendations=[
                    CpicRecommendation(
                        drug="clopidogrel",
                        recommendation="Consider alternative",
                        citation="CPIC: Clopidogrel and CYP2C19 — 2022 update",
                    )
                ],
            )
        ],
    )
    summary = SummarizerOutput(
        summary="Stub summary with low confidence.",
        key_findings=[
            SummarizerFinding(
                gene="CYP2C19",
                phenotype="Intermediate Metabolizer",
                drug="clopidogrel",
            )
        ],
        citations=[
            SummarizerCitation(source="CPIC", guideline="Clopidogrel and CYP2C19 — 2022 update")
        ],
        confidence=0.5,
    )

    event = {
        **summary.model_dump(mode="json"),
        "job_id": "j_crit1",
        "analyzer": analyzer.model_dump(mode="json"),
        "bundle_s3_url": f"s3://{reports_bucket}/{bundle_key}",
    }

    result = handler(event, None)
    assert result["verdict"] == "reject"
    assert "low_confidence" in result["reasons"]
