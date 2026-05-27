"""Unit tests for service.common.models.

Covers schema validation, enum coverage, the strict-extras / immutability
policy enforced by ``_StrictModel``, and the contracts described in
``AGENTS.md``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from service.common.models import (
    AgentName,
    AnalyzerCall,
    CpicRecommendation,
    CriticVerdict,
    FailureReason,
    IntakeOutput,
    JobRecord,
    JobStatus,
    SubmitJobRequest,
    SummarizerCitation,
    SummarizerFinding,
    SummarizerOutput,
    VariantCall,
    utcnow,
)


class TestSubmitJobRequest:
    def test_accepts_valid_s3_url(self) -> None:
        req = SubmitJobRequest(sample_id="S-001", vcf_url="s3://bucket/path/sample.vcf")
        assert req.sample_id == "S-001"
        assert req.vcf_url.startswith("s3://")

    def test_rejects_non_s3_url(self) -> None:
        with pytest.raises(ValidationError):
            SubmitJobRequest(sample_id="S-001", vcf_url="https://example.com/sample.vcf")

    @pytest.mark.parametrize("bad", ["", "x" * 65])
    def test_sample_id_length_bounds(self, bad: str) -> None:
        with pytest.raises(ValidationError):
            SubmitJobRequest(sample_id=bad, vcf_url="s3://bucket/sample.vcf")

    def test_extras_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            SubmitJobRequest.model_validate(
                {
                    "sample_id": "S-001",
                    "vcf_url": "s3://bucket/sample.vcf",
                    "rogue_field": True,
                }
            )

    def test_model_is_frozen(self) -> None:
        req = SubmitJobRequest(sample_id="S-001", vcf_url="s3://bucket/sample.vcf")
        with pytest.raises(ValidationError):
            req.sample_id = "S-002"  # type: ignore[misc]

    def test_strips_whitespace(self) -> None:
        req = SubmitJobRequest(sample_id="  S-001  ", vcf_url="s3://bucket/sample.vcf")
        assert req.sample_id == "S-001"


class TestJobRecord:
    def _row(self, **overrides: object) -> JobRecord:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        base: dict[str, object] = {
            "job_id": "j_abc",
            "sample_id": "S-001",
            "status": JobStatus.PENDING,
            "correlation_id": "c-001",
            "vcf_url": "s3://bucket/sample.vcf",
            "created_at": now,
            "updated_at": now,
        }
        base.update(overrides)
        return JobRecord.model_validate(base)

    def test_defaults(self) -> None:
        row = self._row()
        assert row.report_ready is False
        assert row.current_step is None
        assert row.failure_reason is None

    def test_status_enum_serialises_to_value(self) -> None:
        row = self._row(status=JobStatus.SUCCEEDED, report_ready=True)
        dumped = row.model_dump(mode="json")
        assert dumped["status"] == "succeeded"
        assert dumped["report_ready"] is True

    def test_failure_reason_stored_as_enum(self) -> None:
        row = self._row(
            status=JobStatus.FAILED,
            failure_reason=FailureReason.LOW_CONFIDENCE,
        )
        assert row.failure_reason is FailureReason.LOW_CONFIDENCE


class TestAgentEnums:
    def test_agent_name_values(self) -> None:
        assert {a.value for a in AgentName} == {
            "intake",
            "analyzer",
            "fhir_composer",
            "summarizer",
            "critic",
        }

    def test_failure_reason_covers_critic_refusals(self) -> None:
        refusals = {
            FailureReason.MISSING_CPIC_CITATION.value,
            FailureReason.UNKNOWN_DRUG_NAME.value,
            FailureReason.LOW_CONFIDENCE.value,
            FailureReason.BEDROCK_DISABLED.value,
        }
        assert refusals == {
            "missing_cpic_citation",
            "unknown_drug_name",
            "low_confidence",
            "bedrock_disabled",
        }


class TestIntakeOutput:
    def test_round_trip(self) -> None:
        out = IntakeOutput(
            job_id="j_1",
            sample_id="S-1",
            sample_class="exome",
            variants=[VariantCall(chrom="10", pos=96541616, ref="G", alt="A", gene="CYP2C19")],
        )
        as_json = out.model_dump_json()
        assert "CYP2C19" in as_json
        assert IntakeOutput.model_validate_json(as_json) == out

    def test_rejects_invalid_sample_class(self) -> None:
        with pytest.raises(ValidationError):
            IntakeOutput(
                job_id="j_1",
                sample_id="S-1",
                sample_class="genome",  # type: ignore[arg-type]
                variants=[],
            )

    def test_rejects_non_positive_position(self) -> None:
        with pytest.raises(ValidationError):
            VariantCall(chrom="10", pos=0, ref="G", alt="A")


class TestAnalyzerCall:
    def test_recommendations_default_empty(self) -> None:
        call = AnalyzerCall(
            gene="CYP2C19",
            genotype="*1/*2",
            phenotype="Intermediate Metabolizer",
        )
        assert call.cpic_recommendations == []

    def test_recommendation_requires_citation(self) -> None:
        with pytest.raises(ValidationError):
            CpicRecommendation(drug="clopidogrel", recommendation="Consider alt", citation="")


class TestSummarizerOutput:
    def _ok_payload(self) -> dict[str, object]:
        finding = SummarizerFinding(
            gene="CYP2C19",
            phenotype="Intermediate Metabolizer",
            drug="clopidogrel",
        )
        citation = SummarizerCitation(
            source="CPIC",
            guideline="Clopidogrel and CYP2C19 — 2022 update",
        )
        return {
            "summary": "Patient is a CYP2C19 intermediate metabolizer.",
            "key_findings": [finding.model_dump()],
            "citations": [citation.model_dump()],
            "confidence": 0.8,
        }

    def test_round_trip(self) -> None:
        out = SummarizerOutput.model_validate(self._ok_payload())
        assert out.confidence == pytest.approx(0.8)
        assert out.citations[0].source == "CPIC"

    def test_confidence_upper_bound(self) -> None:
        payload = self._ok_payload()
        payload["confidence"] = 1.5
        with pytest.raises(ValidationError):
            SummarizerOutput.model_validate(payload)

    def test_confidence_lower_bound(self) -> None:
        payload = self._ok_payload()
        payload["confidence"] = -0.1
        with pytest.raises(ValidationError):
            SummarizerOutput.model_validate(payload)


class TestCriticVerdict:
    def test_approve_no_reasons_ok(self) -> None:
        v = CriticVerdict(verdict="approve")
        assert v.reasons == []
        assert v.notes == ""

    def test_reject_with_reasons(self) -> None:
        v = CriticVerdict(
            verdict="reject",
            reasons=[FailureReason.LOW_CONFIDENCE],
            notes="confidence below threshold",
        )
        assert v.reasons[0] is FailureReason.LOW_CONFIDENCE
        assert v.notes == "confidence below threshold"

    def test_rejects_unknown_verdict(self) -> None:
        with pytest.raises(ValidationError):
            CriticVerdict.model_validate({"verdict": "maybe"})


def test_utcnow_is_utc_aware() -> None:
    ts = utcnow()
    assert ts.tzinfo is not None
    offset = ts.utcoffset()
    assert offset is not None
    assert offset.total_seconds() == 0
