"""Unit tests for CPIC subset rule matching."""

from __future__ import annotations

import pytest

from service.agents.analyzer.cpic_rules import analyze_intake, load_rules
from service.common.errors import PipelineError
from service.common.models import FailureReason, IntakeOutput, VariantCall


@pytest.mark.unit
def test_load_rules() -> None:
    rules = load_rules()
    assert len(rules) >= 2


@pytest.mark.unit
def test_analyze_matches_cyp2c19() -> None:
    intake = IntakeOutput(
        job_id="j_1",
        sample_id="S-1",
        sample_class="panel",
        variants=[
            VariantCall(chrom="10", pos=96541616, ref="G", alt="A", gene="CYP2C19"),
        ],
    )
    output = analyze_intake(intake)
    assert len(output.calls) == 1
    assert output.calls[0].gene == "CYP2C19"
    assert output.calls[0].cpic_recommendations[0].drug == "clopidogrel"


@pytest.mark.unit
def test_analyze_no_rules_is_not_error() -> None:
    intake = IntakeOutput(
        job_id="j_2",
        sample_id="S-2",
        sample_class="other",
        variants=[
            VariantCall(chrom="1", pos=100, ref="A", alt="G", gene="UNKNOWN"),
        ],
    )
    output = analyze_intake(intake)
    assert output.calls == []


@pytest.mark.unit
def test_conflicting_genotype_raises() -> None:
    rules = [
        {
            "gene": "CYP2C19",
            "variant": {"chrom": "10", "pos": 96541616, "ref": "G", "alt": "A"},
            "genotype": "*1/*2",
            "phenotype": "Intermediate Metabolizer",
            "recommendations": [],
        },
        {
            "gene": "CYP2C19",
            "variant": {"chrom": "10", "pos": 96541616, "ref": "G", "alt": "A"},
            "genotype": "*2/*2",
            "phenotype": "Poor Metabolizer",
            "recommendations": [],
        },
    ]
    intake = IntakeOutput(
        job_id="j_3",
        sample_id="S-3",
        sample_class="panel",
        variants=[
            VariantCall(chrom="10", pos=96541616, ref="G", alt="A", gene="CYP2C19"),
        ],
    )
    with pytest.raises(PipelineError) as exc:
        analyze_intake(intake, rules=rules)
    assert exc.value.reason == FailureReason.CONFLICTING_GENOTYPE
