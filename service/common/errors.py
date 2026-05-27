"""Error envelope and :class:`ServiceError` hierarchy used at the API boundary.

Every API Lambda handler should look like::

    from service.common.errors import ServiceError, to_api_response

    def handler(event: dict, context: object) -> dict:
        try:
            ...
        except ServiceError as err:
            return to_api_response(err)
        except Exception as err:
            return to_api_response(ServiceError.internal(err))

Internal agent code raises :class:`PipelineError` (a ``ServiceError``
subclass that carries a stable :class:`FailureReason`). Step Functions
catches it and routes the job into the clean ``failed`` state in
DynamoDB.

The envelope shape is intentionally narrow — no stack traces, no PHI,
just a stable machine-readable code, a human-readable message, and
optional structural details.
"""

from __future__ import annotations

import http
import json
from typing import Any, ClassVar

from service.common.models import FailureReason


class ServiceError(Exception):
    """Base class for all errors raised by service code."""

    code: ClassVar[str] = "INTERNAL_ERROR"
    status_code: ClassVar[int] = http.HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = dict(details) if details else {}
        if cause is not None:
            self.__cause__ = cause

    def to_envelope(self) -> dict[str, Any]:
        envelope: dict[str, Any] = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.details:
            envelope["error"]["details"] = self.details
        return envelope

    @classmethod
    def internal(cls, cause: BaseException) -> ServiceError:
        """Wrap an unexpected exception without leaking its message.

        Only the exception class name is exposed; the underlying message
        may contain sensitive context and is intentionally dropped.
        """

        return ServiceError(
            "internal server error",
            details={"error_class": type(cause).__name__},
            cause=cause,
        )


class ValidationError(ServiceError):
    """Caller sent a malformed request body or query parameter."""

    code = "VALIDATION_ERROR"
    status_code = http.HTTPStatus.BAD_REQUEST


class NotFoundError(ServiceError):
    """Requested resource (e.g. a job id) does not exist."""

    code = "NOT_FOUND"
    status_code = http.HTTPStatus.NOT_FOUND


class JobNotReadyError(ServiceError):
    """Report requested for a job that has not finished yet."""

    code = "JOB_NOT_READY"
    status_code = http.HTTPStatus.CONFLICT


class UpstreamError(ServiceError):
    """A downstream AWS dependency failed and we cannot recover at the API."""

    code = "UPSTREAM_ERROR"
    status_code = http.HTTPStatus.BAD_GATEWAY


class PipelineError(ServiceError):
    """Raised inside an agent; carries a stable :class:`FailureReason`.

    Step Functions catches this and writes a clean ``failed`` row to
    DynamoDB with ``failure_reason = <reason>.value``.
    """

    code = "PIPELINE_ERROR"
    status_code = http.HTTPStatus.UNPROCESSABLE_ENTITY

    def __init__(
        self,
        reason: FailureReason,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, details=details, cause=cause)
        self.reason = reason

    def to_envelope(self) -> dict[str, Any]:
        envelope = super().to_envelope()
        envelope["error"]["reason"] = self.reason.value
        return envelope


def to_api_response(err: ServiceError) -> dict[str, Any]:
    """Render ``err`` as an API Gateway HTTP API v2 proxy response.

    Always returns JSON; never includes a stack trace or PHI.
    """

    return {
        "statusCode": int(err.status_code),
        "headers": {"content-type": "application/json"},
        "body": json.dumps(err.to_envelope(), separators=(",", ":")),
    }
