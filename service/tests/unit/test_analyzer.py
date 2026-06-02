"""Unit tests for Analyzer handler."""

from __future__ import annotations

import pytest

from service.agents.analyzer.handler import handler
from service.common.models import IntakeOutput, VariantCall
from service.tests.conftest import seed_job


@pytest.mark.unit
def test_analyzer_handler_returns_calls(
    monkeypatch: pytest.MonkeyPatch,
    jobs_table: str,
    agent_runs_table: str,
    moto_env: None,
) -> None:
    monkeypatch.setenv("JOBS_TABLE", jobs_table)
    monkeypatch.setenv("AGENT_RUNS_TABLE", agent_runs_table)
    monkeypatch.setenv("AGENT_NAME", "analyzer")

    seed_job("j_analyze1")

    event = IntakeOutput(
        job_id="j_analyze1",
        sample_id="S-1",
        sample_class="panel",
        variants=[
            VariantCall(chrom="10", pos=96541616, ref="G", alt="A", gene="CYP2C19"),
        ],
    ).model_dump(mode="json")

    result = handler(event, None)
    assert result["job_id"] == "j_analyze1"
    assert len(result["calls"]) == 1
