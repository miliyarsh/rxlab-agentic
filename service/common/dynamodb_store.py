"""DynamoDB persistence helpers for JobRecord and AgentRunRecord."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

import boto3
from botocore.exceptions import ClientError

from service.common.errors import NotFoundError, UpstreamError
from service.common.models import (
    AgentName,
    AgentRunRecord,
    AuditRecord,
    JobRecord,
    JobStatus,
    utcnow,
)


def _table_name(env_var: str) -> str:
    name = os.environ.get(env_var, "")
    if not name:
        raise RuntimeError(f"missing required environment variable: {env_var}")
    return name


def _serialize_datetime(value: datetime) -> str:
    return value.astimezone().isoformat()


def _deserialize_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def job_record_to_item(record: JobRecord) -> dict[str, Any]:
    data = record.model_dump()
    data["status"] = record.status.value
    if record.current_step is not None:
        data["current_step"] = record.current_step.value
    else:
        data.pop("current_step", None)
    if record.failure_reason is not None:
        data["failure_reason"] = record.failure_reason.value
    else:
        data.pop("failure_reason", None)
    data["created_at"] = _serialize_datetime(record.created_at)
    data["updated_at"] = _serialize_datetime(record.updated_at)
    return data


def job_record_from_item(item: dict[str, Any]) -> JobRecord:
    payload = dict(item)
    payload["created_at"] = _deserialize_datetime(str(payload["created_at"]))
    payload["updated_at"] = _deserialize_datetime(str(payload["updated_at"]))
    return JobRecord.model_validate(payload)


def agent_run_to_item(record: AgentRunRecord) -> dict[str, Any]:
    data = record.model_dump()
    data["agent"] = record.agent.value
    data["started_at"] = _serialize_datetime(record.started_at)
    if record.ended_at is not None:
        data["ended_at"] = _serialize_datetime(record.ended_at)
    else:
        data.pop("ended_at", None)
    return data


def audit_record_to_item(record: AuditRecord, *, expires_at: datetime) -> dict[str, Any]:
    data = record.model_dump()
    data["agent"] = record.agent.value
    data["event"] = record.event
    if record.verdict is not None:
        data["verdict"] = record.verdict
    else:
        data.pop("verdict", None)
    data["reasons"] = [r.value for r in record.reasons]
    data["created_at"] = _serialize_datetime(record.created_at)
    data["expires_at"] = _serialize_datetime(expires_at)
    return data


class JobsStore:
    def __init__(self, *, table_name: str | None = None, client: Any | None = None) -> None:
        self._table_name = table_name or _table_name("JOBS_TABLE")
        self._client = client or boto3.client("dynamodb")

    def put_job(self, record: JobRecord) -> None:
        item = job_record_to_item(record)
        try:
            self._client.put_item(
                TableName=self._table_name,
                Item=_item_to_dynamo(item),
                ConditionExpression="attribute_not_exists(job_id)",
            )
        except ClientError as err:
            if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise UpstreamError("job already exists", cause=err) from err
            raise UpstreamError("failed to write job record", cause=err) from err

    def get_job(self, job_id: str) -> JobRecord:
        try:
            response = self._client.get_item(
                TableName=self._table_name,
                Key={"job_id": {"S": job_id}},
            )
        except ClientError as err:
            raise UpstreamError("failed to read job record", cause=err) from err
        item = response.get("Item")
        if not item:
            raise NotFoundError(f"job '{job_id}' not found")
        return job_record_from_item(_from_item(response.get("Item", {})))

    def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        current_step: AgentName | None = None,
        clear_current_step: bool = False,
        report_ready: bool | None = None,
        failure_reason: str | None = None,
        clear_failure_reason: bool = False,
    ) -> JobRecord:
        set_parts: list[str] = ["updated_at = :updated_at"]
        remove_parts: list[str] = []
        names: dict[str, str] = {}
        values: dict[str, Any] = {":updated_at": _serialize_datetime(utcnow())}

        if status is not None:
            set_parts.append("#status = :status")
            names["#status"] = "status"
            values[":status"] = status.value
        if clear_current_step:
            remove_parts.append("current_step")
        elif current_step is not None:
            set_parts.append("current_step = :current_step")
            values[":current_step"] = current_step.value
        if report_ready is not None:
            set_parts.append("report_ready = :report_ready")
            values[":report_ready"] = report_ready
        if clear_failure_reason:
            remove_parts.append("failure_reason")
        elif failure_reason is not None:
            set_parts.append("failure_reason = :failure_reason")
            values[":failure_reason"] = failure_reason

        update_chunks: list[str] = []
        if set_parts:
            update_chunks.append("SET " + ", ".join(set_parts))
        if remove_parts:
            update_chunks.append("REMOVE " + ", ".join(remove_parts))
        expr = " ".join(update_chunks)
        kwargs: dict[str, Any] = {
            "TableName": self._table_name,
            "Key": {"job_id": {"S": job_id}},
            "UpdateExpression": expr,
            "ExpressionAttributeValues": _item_to_dynamo(values),
            "ReturnValues": "ALL_NEW",
        }
        if names:
            kwargs["ExpressionAttributeNames"] = names

        try:
            response = self._client.update_item(**kwargs)
        except ClientError as err:
            raise UpstreamError("failed to update job record", cause=err) from err
        return job_record_from_item(_from_item(response["Attributes"]))


class AgentRunsStore:
    def __init__(self, *, table_name: str | None = None, client: Any | None = None) -> None:
        self._table_name = table_name or _table_name("AGENT_RUNS_TABLE")
        self._client = client or boto3.client("dynamodb")

    def put_run(self, record: AgentRunRecord) -> None:
        try:
            self._client.put_item(
                TableName=self._table_name,
                Item=_item_to_dynamo(agent_run_to_item(record)),
            )
        except ClientError as err:
            raise UpstreamError("failed to write agent run record", cause=err) from err


class AuditStore:
    def __init__(self, *, table_name: str | None = None, client: Any | None = None) -> None:
        self._table_name = table_name or _table_name("AUDIT_TABLE")
        self._client = client or boto3.client("dynamodb")

    def put_audit(self, record: AuditRecord, *, ttl_days: int = 90) -> None:
        expires_at = record.created_at + timedelta(days=ttl_days)
        try:
            self._client.put_item(
                TableName=self._table_name,
                Item=_item_to_dynamo(audit_record_to_item(record, expires_at=expires_at)),
            )
        except ClientError as err:
            raise UpstreamError("failed to write audit record", cause=err) from err


def _item_to_dynamo(item: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(key): _attr(value) for key, value in item.items()}


def _attr(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {"M": {str(k): _attr(v) for k, v in value.items()}}
    if isinstance(value, list):
        return {"L": [_attr(v) for v in value]}
    if value is None:
        return {"NULL": True}
    if isinstance(value, bool):
        return {"BOOL": value}
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return {"N": str(value)}
    if isinstance(value, StrEnum):
        return {"S": value.value}
    return {"S": str(value)}


def _from_item(item: dict[str, Any]) -> dict[str, Any]:
    return {key: _from_dynamo(value) for key, value in item.items()}


def _from_dynamo(value: dict[str, Any]) -> Any:
    if "S" in value:
        return value["S"]
    if "N" in value:
        num = value["N"]
        return int(num) if "." not in num else float(num)
    if "BOOL" in value:
        return value["BOOL"]
    if "NULL" in value:
        return None
    if "L" in value:
        return [_from_dynamo(v) for v in value["L"]]
    if "M" in value:
        return {k: _from_dynamo(v) for k, v in value["M"].items()}
    raise ValueError(f"unsupported DynamoDB attribute: {value!r}")
