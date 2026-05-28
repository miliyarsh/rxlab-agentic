"""Summarizer output schema — re-export + citation validation helpers."""

from __future__ import annotations

from service.common.models import SummarizerCitation, SummarizerFinding, SummarizerOutput

__all__ = ["SummarizerCitation", "SummarizerFinding", "SummarizerOutput"]


def citations_include_cpic(output: SummarizerOutput) -> bool:
    """Return True when at least one structured CPIC citation is present."""

    return any(c.source == "CPIC" and c.guideline.strip() for c in output.citations)
