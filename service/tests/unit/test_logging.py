"""Unit tests for service.common.logging."""

from __future__ import annotations

import io
import json
import logging
from collections.abc import Iterator
from typing import cast

import pytest

from service.common.logging import JsonFormatter, get_logger


@pytest.fixture
def stream_logger() -> Iterator[tuple[logging.Logger, io.StringIO]]:
    """A logger that writes JSON to an in-memory buffer for assertions."""

    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter())
    log = logging.Logger("rxlab.test", level=logging.INFO)
    log.addHandler(handler)
    log.propagate = False
    try:
        yield log, buf
    finally:
        handler.close()


def _parse_lines(buf: io.StringIO) -> list[dict[str, object]]:
    return [
        cast(dict[str, object], json.loads(line)) for line in buf.getvalue().splitlines() if line
    ]


class TestJsonFormatter:
    def test_basic_fields(self, stream_logger: tuple[logging.Logger, io.StringIO]) -> None:
        log, buf = stream_logger
        log.info("intake.started")
        [record] = _parse_lines(buf)
        assert record["message"] == "intake.started"
        assert record["level"] == "INFO"
        assert record["logger"] == "rxlab.test"
        ts = cast(str, record["timestamp"])
        assert ts.endswith("Z")

    def test_context_fields(self, stream_logger: tuple[logging.Logger, io.StringIO]) -> None:
        log, buf = stream_logger
        log.info(
            "intake.started",
            extra={
                "correlation_id": "c-1",
                "job_id": "j_1",
                "agent": "intake",
                "step": "validate",
            },
        )
        [record] = _parse_lines(buf)
        assert record["correlation_id"] == "c-1"
        assert record["job_id"] == "j_1"
        assert record["agent"] == "intake"
        assert record["step"] == "validate"

    def test_context_fields_are_omitted_when_absent(
        self, stream_logger: tuple[logging.Logger, io.StringIO]
    ) -> None:
        log, buf = stream_logger
        log.info("plain.event")
        [record] = _parse_lines(buf)
        assert "correlation_id" not in record
        assert "job_id" not in record

    def test_arbitrary_extras_are_serialised(
        self, stream_logger: tuple[logging.Logger, io.StringIO]
    ) -> None:
        log, buf = stream_logger
        log.info("metric", extra={"variant_count": 42, "drugs": ["clopidogrel"]})
        [record] = _parse_lines(buf)
        assert record["variant_count"] == 42
        assert record["drugs"] == ["clopidogrel"]

    def test_exotic_types_fall_back_to_repr(
        self, stream_logger: tuple[logging.Logger, io.StringIO]
    ) -> None:
        log, buf = stream_logger

        class Custom:
            def __repr__(self) -> str:
                return "Custom()"

        log.info("event", extra={"obj": Custom()})
        [record] = _parse_lines(buf)
        assert record["obj"] == "Custom()"

    def test_exception_info_captured(
        self, stream_logger: tuple[logging.Logger, io.StringIO]
    ) -> None:
        log, buf = stream_logger
        try:
            raise ValueError("boom")
        except ValueError:
            log.exception("bedrock.error", extra={"error_code": "BEDROCK_ERROR"})
        [record] = _parse_lines(buf)
        assert record["error_code"] == "BEDROCK_ERROR"
        exc_info = cast(str, record["exc_info"])
        assert "ValueError" in exc_info

    def test_single_line_per_record(
        self, stream_logger: tuple[logging.Logger, io.StringIO]
    ) -> None:
        log, buf = stream_logger
        log.info("first")
        log.warning("second")
        lines = buf.getvalue().splitlines()
        assert len(lines) == 2
        for line in lines:
            assert "\n" not in line
            json.loads(line)


class TestGetLogger:
    def test_returns_same_logger_on_repeated_calls(self) -> None:
        a = get_logger("rxlab.unit.repeat")
        b = get_logger("rxlab.unit.repeat")
        assert a is b
        assert len(a.handlers) == 1

    def test_does_not_propagate(self) -> None:
        log = get_logger("rxlab.unit.propagate")
        assert log.propagate is False

    def test_default_level_is_info(self) -> None:
        log = get_logger("rxlab.unit.level")
        assert log.level == logging.INFO
