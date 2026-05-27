"""Structured JSON logging for every Lambda in the service.

Every log line is emitted as a single JSON object containing, at minimum:

* ``timestamp`` — ISO-8601 UTC timestamp
* ``level``     — log level name (``INFO``, ``ERROR``, …)
* ``logger``    — module that produced the line
* ``message``   — short event name (snake_case preferred, e.g. ``intake.started``)

Callers add structural context via ``extra=`` — any of the
:data:`_CONTEXT_FIELDS` keys plus arbitrary scalars/lists/dicts that are
JSON-serialisable.

**PHI is never logged.** Patient narrative, raw genotype, raw VCF
content, and full Bedrock prompt/response bodies are forbidden. Log
counts, identifiers, and structural fields only.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

# Attributes already present on every ``LogRecord``; we never re-emit them
# as ``extra`` fields.
_RESERVED_LOG_ATTRS: frozenset[str] = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
        "taskName",
    }
)

# Context fields surfaced as top-level JSON keys when present on the record.
_CONTEXT_FIELDS: tuple[str, ...] = (
    "correlation_id",
    "job_id",
    "agent",
    "step",
    "error_class",
    "error_message",
    "error_code",
)


class JsonFormatter(logging.Formatter):
    """Format each :class:`logging.LogRecord` as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": _ts(record.created),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in _CONTEXT_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_ATTRS or key in payload or key.startswith("_"):
                continue
            payload[key] = _coerce(value)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, separators=(",", ":"), default=str)


def _ts(epoch: float) -> str:
    return (
        datetime.fromtimestamp(epoch, tz=UTC)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _coerce(value: object) -> object:
    """Make ``value`` JSON-serialisable; fall back to ``repr`` for exotic types."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_coerce(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _coerce(v) for k, v in value.items()}
    return repr(value)


_LOGGER_CACHE: dict[str, logging.Logger] = {}


def get_logger(name: str, *, level: int | str = logging.INFO) -> logging.Logger:
    """Return a configured logger that emits JSON to stderr.

    AWS Lambda captures stderr into CloudWatch Logs, so no further wiring
    is required at runtime.

    The function is **idempotent**: repeated calls with the same ``name``
    return the same logger and never duplicate handlers, which matters
    under Lambda warm starts.
    """

    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not any(isinstance(h, _RxLabJsonHandler) for h in logger.handlers):
        handler = _RxLabJsonHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    _LOGGER_CACHE[name] = logger
    return logger


class _RxLabJsonHandler(logging.StreamHandler):  # type: ignore[type-arg]
    """Marker subclass so we can detect our own handler under warm starts."""

    def __init__(self) -> None:
        super().__init__(stream=sys.stderr)
