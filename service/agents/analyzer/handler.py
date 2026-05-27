"""Analyzer agent — map intake variants to CPIC recommendations."""

from __future__ import annotations

from typing import Any

from service.agents.analyzer.cpic_rules import analyze_intake
from service.common.errors import PipelineError
from service.common.logging import get_logger
from service.common.models import AgentName, FailureReason, IntakeOutput
from service.common.pipeline import agent_name_from_env, track_agent_run

logger = get_logger(__name__)


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    agent = agent_name_from_env(AgentName.ANALYZER)
    try:
        intake = IntakeOutput.model_validate(event)
    except Exception as err:
        raise PipelineError(
            FailureReason.INVALID_VCF_SCHEMA,
            "invalid intake payload for analyzer",
            cause=err,
        ) from err

    with track_agent_run(job_id=intake.job_id, agent=agent):
        output = analyze_intake(intake)
        logger.info(
            "analyzer.completed",
            extra={"job_id": intake.job_id, "call_count": len(output.calls)},
        )
        return output.model_dump(mode="json")
