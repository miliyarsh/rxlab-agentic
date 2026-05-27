"""CPIC subset rule engine for the Analyzer agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from service.common.errors import PipelineError
from service.common.models import (
    AnalyzerCall,
    AnalyzerOutput,
    CpicRecommendation,
    FailureReason,
    IntakeOutput,
    VariantCall,
)

_RULES_PATH = Path(__file__).resolve().parent / "data" / "cpic_subset.json"


def load_rules(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or _RULES_PATH
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except OSError as err:
        raise PipelineError(
            FailureReason.RULE_DATA_LOAD_ERROR,
            "failed to read CPIC subset file",
            cause=err,
        ) from err
    except json.JSONDecodeError as err:
        raise PipelineError(
            FailureReason.RULE_DATA_LOAD_ERROR,
            "CPIC subset file is not valid JSON",
            cause=err,
        ) from err

    rules = raw.get("rules")
    if not isinstance(rules, list):
        raise PipelineError(FailureReason.RULE_DATA_LOAD_ERROR, "CPIC subset missing rules array")
    return rules


def _variant_matches(rule_variant: dict[str, Any], variant: VariantCall) -> bool:
    return (
        str(rule_variant.get("chrom")) == variant.chrom
        and int(rule_variant.get("pos", -1)) == variant.pos
        and str(rule_variant.get("ref")) == variant.ref
        and str(rule_variant.get("alt")) == variant.alt
    )


def analyze_intake(
    intake: IntakeOutput, rules: list[dict[str, Any]] | None = None
) -> AnalyzerOutput:
    rule_data = rules if rules is not None else load_rules()
    calls_by_gene: dict[str, AnalyzerCall] = {}

    for rule in rule_data:
        gene = str(rule.get("gene", ""))
        matched = any(
            _variant_matches(rule["variant"], variant)
            for variant in intake.variants
            if isinstance(rule.get("variant"), dict)
        )
        if not matched:
            continue

        recs = [
            CpicRecommendation(
                drug=str(item["drug"]),
                recommendation=str(item["recommendation"]),
                citation=str(item["citation"]),
            )
            for item in rule.get("recommendations", [])
            if isinstance(item, dict)
        ]
        call = AnalyzerCall(
            gene=gene,
            genotype=str(rule.get("genotype", "")),
            phenotype=str(rule.get("phenotype", "")),
            cpic_recommendations=recs,
        )
        if gene in calls_by_gene and calls_by_gene[gene].genotype != call.genotype:
            raise PipelineError(
                FailureReason.CONFLICTING_GENOTYPE,
                f"conflicting genotype calls for gene {gene}",
            )
        calls_by_gene[gene] = call

    return AnalyzerOutput(job_id=intake.job_id, calls=list(calls_by_gene.values()))
