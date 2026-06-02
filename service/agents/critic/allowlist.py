"""Deterministic guardrails for the Critic agent."""

from __future__ import annotations

from service.agents.summarizer.schema import citations_include_cpic
from service.common.models import AnalyzerOutput, FailureReason, SummarizerOutput


def build_drug_allowlist(analyzer: AnalyzerOutput) -> set[str]:
    drugs: set[str] = set()
    for call in analyzer.calls:
        for rec in call.cpic_recommendations:
            drugs.add(rec.drug.lower())
    return drugs


def find_unknown_drugs(summary: SummarizerOutput, allowlist: set[str]) -> list[str]:
    unknown: list[str] = []
    for finding in summary.key_findings:
        if finding.drug.lower() not in allowlist:
            unknown.append(finding.drug)
    return sorted(set(unknown))


def deterministic_refusal_reasons(
    summary: SummarizerOutput,
    analyzer: AnalyzerOutput,
    *,
    confidence_threshold: float = 0.6,
) -> list[FailureReason]:
    reasons: list[FailureReason] = []
    if summary.confidence < confidence_threshold:
        reasons.append(FailureReason.LOW_CONFIDENCE)
    if not citations_include_cpic(summary):
        reasons.append(FailureReason.MISSING_CPIC_CITATION)
    allowlist = build_drug_allowlist(analyzer)
    if find_unknown_drugs(summary, allowlist):
        reasons.append(FailureReason.UNKNOWN_DRUG_NAME)
    return reasons
