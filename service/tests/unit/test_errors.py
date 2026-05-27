"""Unit tests for service.common.errors."""

from __future__ import annotations

import http
import json

import pytest

from service.common.errors import (
    JobNotReadyError,
    NotFoundError,
    PipelineError,
    ServiceError,
    UpstreamError,
    ValidationError,
    to_api_response,
)
from service.common.models import FailureReason


class TestServiceError:
    def test_default_code_and_status(self) -> None:
        err = ServiceError("oops")
        assert err.code == "INTERNAL_ERROR"
        assert err.status_code == http.HTTPStatus.INTERNAL_SERVER_ERROR

    def test_envelope_includes_details_when_present(self) -> None:
        err = ServiceError("bad", details={"field": "vcf_url"})
        env = err.to_envelope()
        assert env == {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "bad",
                "details": {"field": "vcf_url"},
            }
        }

    def test_envelope_omits_empty_details(self) -> None:
        err = ServiceError("bad")
        assert "details" not in err.to_envelope()["error"]

    def test_internal_wraps_cause_without_leaking_message(self) -> None:
        cause = RuntimeError("filesystem on fire")
        err = ServiceError.internal(cause)
        assert err.__cause__ is cause
        assert err.details == {"error_class": "RuntimeError"}
        assert "filesystem" not in err.message

    def test_message_is_exception_str(self) -> None:
        err = ServiceError("hello")
        assert str(err) == "hello"


class TestSubclasses:
    @pytest.mark.parametrize(
        ("cls", "expected_code", "expected_status"),
        [
            (ValidationError, "VALIDATION_ERROR", http.HTTPStatus.BAD_REQUEST),
            (NotFoundError, "NOT_FOUND", http.HTTPStatus.NOT_FOUND),
            (JobNotReadyError, "JOB_NOT_READY", http.HTTPStatus.CONFLICT),
            (UpstreamError, "UPSTREAM_ERROR", http.HTTPStatus.BAD_GATEWAY),
        ],
    )
    def test_codes_and_statuses(
        self,
        cls: type[ServiceError],
        expected_code: str,
        expected_status: int,
    ) -> None:
        err = cls("nope")
        assert err.code == expected_code
        assert err.status_code == expected_status


class TestPipelineError:
    def test_envelope_includes_reason(self) -> None:
        err = PipelineError(FailureReason.INVALID_VCF_SCHEMA, "bad header")
        env = err.to_envelope()
        assert env["error"]["reason"] == "invalid_vcf_schema"
        assert err.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY

    def test_reason_is_enum_instance(self) -> None:
        err = PipelineError(FailureReason.TOKEN_BUDGET_EXCEEDED, "budget hit")
        assert err.reason is FailureReason.TOKEN_BUDGET_EXCEEDED

    def test_carries_details_and_cause(self) -> None:
        cause = RuntimeError("downstream")
        err = PipelineError(
            FailureReason.BEDROCK_ERROR,
            "Bedrock failure",
            details={"latency_ms": 1234},
            cause=cause,
        )
        env = err.to_envelope()
        assert env["error"]["details"] == {"latency_ms": 1234}
        assert err.__cause__ is cause


class TestToApiResponse:
    def test_returns_apigw_v2_proxy_shape(self) -> None:
        err = ValidationError("missing sample_id")
        resp = to_api_response(err)
        assert resp["statusCode"] == 400
        assert resp["headers"]["content-type"] == "application/json"
        body = json.loads(resp["body"])
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert body["error"]["message"] == "missing sample_id"

    def test_pipeline_error_round_trip(self) -> None:
        err = PipelineError(FailureReason.TOKEN_BUDGET_EXCEEDED, "budget hit")
        body = json.loads(to_api_response(err)["body"])
        assert body["error"]["reason"] == "token_budget_exceeded"
        assert body["error"]["code"] == "PIPELINE_ERROR"

    def test_body_is_single_line_json(self) -> None:
        err = ServiceError("ok", details={"a": 1, "b": 2})
        body = to_api_response(err)["body"]
        assert "\n" not in body
        assert json.loads(body)["error"]["details"]["a"] == 1
