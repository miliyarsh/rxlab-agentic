"""Pipeline helpers shared by deterministic agents."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import boto3
from botocore.exceptions import ClientError

from service.common.dynamodb_store import AgentRunsStore, JobsStore
from service.common.errors import PipelineError, UpstreamError
from service.common.logging import get_logger
from service.common.models import AgentName, AgentRunRecord, JobStatus, utcnow

logger = get_logger(__name__)


def agent_name_from_env(default: AgentName) -> AgentName:
    raw = os.environ.get("AGENT_NAME", default.value)
    return AgentName(raw)


def emit_agent_metric(agent: AgentName, *, error: bool = False) -> None:
    namespace = f"RxLab/Agents/{agent.value}"
    metric_name = "ErrorCount" if error else "InvocationCount"
    try:
        boto3.client("cloudwatch").put_metric_data(
            Namespace=namespace,
            MetricData=[{"MetricName": metric_name, "Value": 1.0, "Unit": "Count"}],
        )
    except ClientError:
        logger.warning("metrics.emit_failed", extra={"agent": agent.value, "metric": metric_name})


@contextmanager
def track_agent_run(
    *,
    job_id: str,
    agent: AgentName,
    correlation_id: str | None = None,
    jobs: JobsStore | None = None,
    runs: AgentRunsStore | None = None,
) -> Iterator[None]:
    """Record agent start/end in DynamoDB and update the job's current step."""

    jobs_store = jobs or JobsStore()
    runs_store = runs or AgentRunsStore()
    started = utcnow()
    start_ms = time.perf_counter()

    logger.info(
        "agent.started",
        extra={"job_id": job_id, "agent": agent.value, "correlation_id": correlation_id},
    )
    emit_agent_metric(agent)

    jobs_store.update_job(job_id, status=JobStatus.RUNNING, current_step=agent)
    error_code: str | None = None
    success = False

    try:
        yield
        success = True
    except PipelineError as err:
        error_code = err.reason.value
        emit_agent_metric(agent, error=True)
        jobs_store.update_job(
            job_id,
            status=JobStatus.FAILED,
            failure_reason=err.reason.value,
            clear_current_step=True,
        )
        raise
    except Exception as err:
        error_code = type(err).__name__
        emit_agent_metric(agent, error=True)
        jobs_store.update_job(
            job_id,
            status=JobStatus.FAILED,
            clear_current_step=True,
        )
        raise UpstreamError(f"{agent.value} agent failed", cause=err) from err
    finally:
        latency_ms = int((time.perf_counter() - start_ms) * 1000)
        ended = utcnow()
        runs_store.put_run(
            AgentRunRecord(
                job_id=job_id,
                agent=agent,
                started_at=started,
                ended_at=ended,
                success=success,
                error_code=error_code,
                latency_ms=latency_ms,
            )
        )
        logger.info(
            "agent.finished",
            extra={
                "job_id": job_id,
                "agent": agent.value,
                "correlation_id": correlation_id,
                "success": success,
                "latency_ms": latency_ms,
            },
        )


def mark_job_succeeded(job_id: str, *, jobs: JobsStore | None = None) -> None:
    store = jobs or JobsStore()
    store.update_job(
        job_id,
        status=JobStatus.SUCCEEDED,
        report_ready=True,
        clear_current_step=True,
        clear_failure_reason=True,
    )


def pipeline_error_response(err: PipelineError) -> dict[str, Any]:
    """Shape raised PipelineError for Step Functions (re-raised after logging)."""

    return {
        "error": err.reason.value,
        "message": err.message,
        "details": err.details,
    }
