"""Prompt templates for the Critic Bedrock call."""

from __future__ import annotations

import json

SYSTEM_PROMPT = """You are a pharmacogenomics safety critic.
Return ONLY valid JSON (no markdown):
{
  "verdict": "approve" | "reject",
  "reasons": ["missing_cpic_citation" | "unknown_drug_name" | "low_confidence"],
  "notes": "<= 1 short paragraph>"
}
Approve only when the summary is supported by the CPIC recommendations provided.
Reject if citations are missing, drugs are invented, or confidence is below 0.6.
"""


def build_user_prompt(*, summary: dict[str, object], analyzer: dict[str, object]) -> str:
    return json.dumps(
        {
            "summarizer_output": summary,
            "analyzer_calls": analyzer.get("calls", []),
        },
        separators=(",", ":"),
    )
