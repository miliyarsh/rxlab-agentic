"""Bedrock runtime helpers — imported only by summarizer and critic agents."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.exceptions import ClientError

from service.common.errors import PipelineError
from service.common.models import FailureReason

DEFAULT_BEDROCK_MODEL_ID = "anthropic.claude-haiku-4-5-20251001-v1:0"


@dataclass(frozen=True)
class BedrockConfig:
    model_id: str
    enabled: bool


@dataclass(frozen=True)
class BedrockInvokeResult:
    payload: dict[str, Any]
    tokens_used: int
    latency_ms: int


def load_bedrock_config(environment: str) -> BedrockConfig:
    """Read model id and feature flag from env vars (tests) or SSM (runtime)."""

    env_model = os.environ.get("BEDROCK_MODEL_ID", "")
    env_enabled = os.environ.get("BEDROCK_ENABLED")

    if env_enabled is not None:
        return BedrockConfig(
            model_id=env_model or DEFAULT_BEDROCK_MODEL_ID,
            enabled=env_enabled.lower() == "true",
        )

    if env_model:
        return BedrockConfig(model_id=env_model, enabled=True)

    prefix = f"/rxlab/{environment}/"
    ssm = boto3.client("ssm")
    try:
        model_id = ssm.get_parameter(Name=f"{prefix}bedrock/model_id")["Parameter"]["Value"]
        enabled_raw = ssm.get_parameter(Name=f"{prefix}feature_flags/bedrock_enabled")["Parameter"][
            "Value"
        ]
    except ClientError as err:
        raise PipelineError(
            FailureReason.BEDROCK_ERROR,
            "failed to load Bedrock configuration from SSM",
            cause=err,
        ) from err

    return BedrockConfig(model_id=model_id, enabled=enabled_raw.lower() == "true")


def invoke_claude_json(
    *,
    model_id: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float = 0.2,
) -> BedrockInvokeResult:
    """Invoke Bedrock Claude with JSON-only response instructions."""

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    client = boto3.client("bedrock-runtime")
    start = time.perf_counter()
    try:
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body).encode("utf-8"),
        )
    except ClientError as err:
        raise PipelineError(
            FailureReason.BEDROCK_ERROR,
            "Bedrock invoke failed",
            cause=err,
        ) from err

    latency_ms = int((time.perf_counter() - start) * 1000)
    raw_body = json.loads(response["body"].read())
    text_blocks = raw_body.get("content", [])
    text = ""
    for block in text_blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            text += str(block.get("text", ""))

    text = text.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as err:
        raise PipelineError(
            FailureReason.INVALID_LLM_OUTPUT,
            "Bedrock response was not valid JSON",
            cause=err,
        ) from err

    usage = raw_body.get("usage", {})
    tokens_used = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
    return BedrockInvokeResult(payload=payload, tokens_used=tokens_used, latency_ms=latency_ms)
