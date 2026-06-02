"""Prompt templates for the Summarizer Bedrock call."""

from __future__ import annotations

import json
from typing import Any

SYSTEM_PROMPT = """You are a pharmacogenomics clinical summarizer.
Return ONLY valid JSON matching this schema (no markdown fences):
{
  "summary": "<= 2 short paragraphs plain English>",
  "key_findings": [{"gene": "...", "phenotype": "...", "drug": "..."}],
  "citations": [{"source": "CPIC", "guideline": "..."}],
  "confidence": 0.0
}
Rules:
- Do NOT include patient demographics.
- Only mention drugs present in the provided CPIC recommendations.
- Every key_finding drug MUST appear in the recommendations list.
- citations MUST include at least one entry with source=CPIC copied from the input.
- confidence is 0.0-1.0 reflecting how well the input supports the summary.
"""


def build_user_prompt(*, bundle: dict[str, Any], analyzer: dict[str, Any]) -> str:
    return json.dumps(
        {
            "instruction": "Summarize the pharmacogenomic findings for a clinician.",
            "analyzer_calls": analyzer.get("calls", []),
            "fhir_bundle_resource_types": [
                entry.get("resource", {}).get("resourceType")
                for entry in bundle.get("entry", [])
                if isinstance(entry, dict)
            ],
        },
        separators=(",", ":"),
    )
