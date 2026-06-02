"""Unit tests for Critic v2 deterministic guardrails."""

from __future__ import annotations

import pytest

from service.agents.critic.allowlist import (
    build_drug_allowlist,
    deterministic_refusal_reasons,
    find_unknown_drugs,
)
from service.common.models import (
    AnalyzerCall,
    AnalyzerOutput,
    CpicRecommendation,
    FailureReason,
    SummarizerCitation,
    SummarizerFinding,
    SummarizerOutput,
)


@pytest.mark.unit
def test_low_confidence_refusal() -> None:
    analyzer = AnalyzerOutput(job_id="j1", calls=[])
    summary = SummarizerOutput(
        summary="x",
        key_findings=[],
        citations=[SummarizerCitation(source="CPIC", guideline="g")],
        confidence=0.2,
    )
    reasons = deterministic_refusal_reasons(summary, analyzer)
    assert FailureReason.LOW_CONFIDENCE in reasons


@pytest.mark.unit
def test_missing_cpic_citation_refusal() -> None:
    analyzer = AnalyzerOutput(job_id="j1", calls=[])
    summary = SummarizerOutput(
        summary="x",
        key_findings=[],
        citations=[],
        confidence=0.9,
    )
    reasons = deterministic_refusal_reasons(summary, analyzer)
    assert FailureReason.MISSING_CPIC_CITATION in reasons


@pytest.mark.unit
def test_unknown_drug_refusal() -> None:
    analyzer = AnalyzerOutput(
        job_id="j1",
        calls=[
            AnalyzerCall(
                gene="CYP2C19",
                genotype="*1/*2",
                phenotype="IM",
                cpic_recommendations=[
                    CpicRecommendation(
                        drug="clopidogrel",
                        recommendation="alt",
                        citation="CPIC",
                    )
                ],
            )
        ],
    )
    allowlist = build_drug_allowlist(analyzer)
    assert allowlist == {"clopidogrel"}
    summary = SummarizerOutput(
        summary="mentions warfarin",
        key_findings=[
            SummarizerFinding(gene="CYP2C19", phenotype="IM", drug="warfarin"),
        ],
        citations=[SummarizerCitation(source="CPIC", guideline="g")],
        confidence=0.9,
    )
    assert find_unknown_drugs(summary, allowlist) == ["warfarin"]
    reasons = deterministic_refusal_reasons(summary, analyzer)
    assert FailureReason.UNKNOWN_DRUG_NAME in reasons


@pytest.mark.unit
def test_approve_path_no_refusals() -> None:
    analyzer = AnalyzerOutput(
        job_id="j1",
        calls=[
            AnalyzerCall(
                gene="CYP2C19",
                genotype="*1/*2",
                phenotype="IM",
                cpic_recommendations=[
                    CpicRecommendation(
                        drug="clopidogrel",
                        recommendation="alt",
                        citation="CPIC: Clopidogrel",
                    )
                ],
            )
        ],
    )
    summary = SummarizerOutput(
        summary="Supported summary.",
        key_findings=[
            SummarizerFinding(gene="CYP2C19", phenotype="IM", drug="clopidogrel"),
        ],
        citations=[SummarizerCitation(source="CPIC", guideline="CPIC: Clopidogrel")],
        confidence=0.9,
    )
    assert deterministic_refusal_reasons(summary, analyzer) == []
