"""Unit tests for FHIR Composer."""

from __future__ import annotations

import json

import boto3
import pytest

from service.agents.fhir_composer.fhir_models import build_bundle
from service.agents.fhir_composer.handler import handler
from service.common.models import AnalyzerCall, AnalyzerOutput, CpicRecommendation
from service.tests.conftest import seed_job


@pytest.mark.unit
def test_build_bundle_contains_core_resources() -> None:
    analyzer = AnalyzerOutput(
        job_id="j_fhir1",
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
    built = build_bundle(analyzer)
    bundle = built["bundle"]
    assert bundle["resourceType"] == "Bundle"
    types = {entry["resource"]["resourceType"] for entry in bundle["entry"]}
    assert "Observation" in types
    assert "MedicationStatement" in types
    assert "DocumentReference" in types


@pytest.mark.integration
def test_fhir_handler_writes_bundle(
    moto_env: None,
    aws_region: str,
    jobs_table: str,
    agent_runs_table: str,
    reports_bucket: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JOBS_TABLE", jobs_table)
    monkeypatch.setenv("AGENT_RUNS_TABLE", agent_runs_table)
    monkeypatch.setenv("REPORTS_BUCKET", reports_bucket)
    monkeypatch.setenv("AGENT_NAME", "fhir_composer")

    seed_job("j_fhir2")

    event = AnalyzerOutput(
        job_id="j_fhir2",
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
    ).model_dump(mode="json")

    result = handler(event, None)
    assert result["bundle_s3_url"].startswith(f"s3://{reports_bucket}/j_fhir2/")
    obj = boto3.client("s3", region_name=aws_region).get_object(
        Bucket=reports_bucket,
        Key="j_fhir2/bundle.json",
    )
    bundle = json.loads(obj["Body"].read())
    assert bundle["resourceType"] == "Bundle"
