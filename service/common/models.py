"""Pydantic v2 models shared across the RxLab Agentic service.

These models are the single source of truth for:

* The public API surface (``SubmitJobRequest``, ``SubmitJobResponse``,
  ``GetReportResponse``).
* DynamoDB row shapes (``JobRecord``, ``AgentRunRecord``, ``AuditRecord``).
* Agent I/O contracts, in pipeline order
  (``IntakeOutput`` → ``AnalyzerOutput`` → ``FhirComposerOutput`` →
  ``SummarizerOutput`` → ``CriticVerdict``).

All models inherit from :class:`_StrictModel`, which:

* forbids unknown fields (``extra="forbid"``),
* is frozen (immutable after construction) to keep boundary objects
  side-effect free,
* strips surrounding whitespace from string inputs.

Whenever ``AGENTS.md`` is updated, edit this file first and let the type
checker drive the changes through the rest of the service.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

JobId = str
SampleId = str
CorrelationId = str

S3_URL_PATTERN = r"^s3://[a-zA-Z0-9.\-_]{3,63}/.+$"


class _StrictModel(BaseModel):
    """Base model: forbid extras, immutable, strip string whitespace."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AgentName(StrEnum):
    INTAKE = "intake"
    ANALYZER = "analyzer"
    FHIR_COMPOSER = "fhir_composer"
    SUMMARIZER = "summarizer"
    CRITIC = "critic"


class FailureReason(StrEnum):
    """Stable, machine-readable failure codes.

    Used in :class:`JobRecord.failure_reason`, :class:`AuditRecord.reasons`,
    and :class:`CriticVerdict.reasons`. New values require a documented
    schema extension (see AGENTS.md §5).
    """

    INVALID_VCF_SCHEMA = "invalid_vcf_schema"
    UNREACHABLE_VCF = "unreachable_vcf"
    EMPTY_VCF = "empty_vcf"
    CONFLICTING_GENOTYPE = "conflicting_genotype"
    RULE_DATA_LOAD_ERROR = "rule_data_load_error"
    INVALID_FHIR_PAYLOAD = "invalid_fhir_payload"
    S3_WRITE_FAILED = "s3_write_failed"
    BEDROCK_ERROR = "bedrock_error"
    TOKEN_BUDGET_EXCEEDED = "token_budget_exceeded"  # nosec B105
    INVALID_LLM_OUTPUT = "invalid_llm_output"
    MISSING_CPIC_CITATION = "missing_cpic_citation"
    UNKNOWN_DRUG_NAME = "unknown_drug_name"
    LOW_CONFIDENCE = "low_confidence"
    BEDROCK_DISABLED = "bedrock_disabled"


# ---------------------------------------------------------------------------
# API request / response
# ---------------------------------------------------------------------------


class SubmitJobRequest(_StrictModel):
    sample_id: SampleId = Field(min_length=1, max_length=64)
    vcf_url: str = Field(pattern=S3_URL_PATTERN, max_length=1024)


class SubmitJobResponse(_StrictModel):
    job_id: JobId
    status: Literal["pending"]


class UploadVcfRequest(_StrictModel):
    filename: str = Field(min_length=5, max_length=128, pattern=r"^[\w.-]+\.vcf$")
    content_base64: str = Field(min_length=4, max_length=7_000_000)


class UploadVcfResponse(_StrictModel):
    vcf_url: str = Field(pattern=S3_URL_PATTERN, max_length=1024)
    object_key: str = Field(min_length=1, max_length=512)


class GetJobResponse(_StrictModel):
    job_id: JobId
    status: JobStatus
    current_step: AgentName | None = None
    report_ready: bool = False
    failure_reason: FailureReason | None = None


class GetReportResponse(_StrictModel):
    presigned_url: str
    expires_in_seconds: int = Field(ge=60, le=3600)


# ---------------------------------------------------------------------------
# DynamoDB records
# ---------------------------------------------------------------------------


class JobRecord(_StrictModel):
    """A row in the ``rxlab-jobs`` table."""

    job_id: JobId
    sample_id: SampleId
    status: JobStatus
    current_step: AgentName | None = None
    correlation_id: CorrelationId
    vcf_url: str
    report_ready: bool = False
    failure_reason: FailureReason | None = None
    created_at: datetime
    updated_at: datetime


class AgentRunRecord(_StrictModel):
    """A row in the ``rxlab-agent-runs`` table — one per pipeline step."""

    job_id: JobId
    agent: AgentName
    started_at: datetime
    ended_at: datetime | None = None
    success: bool = False
    error_code: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)


class AuditRecord(_StrictModel):
    """A row in the ``rxlab-audit`` table.

    Audit rows are written by the Critic and by any Bedrock invocation so
    we have a per-job paper trail of AI decisions, token usage, and refusals.
    """

    job_id: JobId
    correlation_id: CorrelationId
    agent: AgentName
    event: Literal["critic_verdict", "bedrock_invocation", "token_budget_exceeded"]
    verdict: Literal["approve", "reject"] | None = None
    reasons: list[FailureReason] = Field(default_factory=list)
    tokens_used: int | None = Field(default=None, ge=0)
    latency_ms: int | None = Field(default=None, ge=0)
    created_at: datetime


# ---------------------------------------------------------------------------
# Pipeline payloads
# ---------------------------------------------------------------------------


class PipelineEvent(_StrictModel):
    """Initial input passed into the Step Functions state machine.

    Every downstream agent's input wraps the previous agent's output with
    these correlation fields so trace context survives every transition.
    """

    job_id: JobId
    sample_id: SampleId
    vcf_url: str
    correlation_id: CorrelationId


# ----- Intake -----


class VariantCall(_StrictModel):
    chrom: str = Field(min_length=1, max_length=8)
    pos: int = Field(ge=1)
    ref: str = Field(min_length=1, max_length=32)
    alt: str = Field(min_length=1, max_length=128)
    gene: str | None = Field(default=None, max_length=32)


class IntakeOutput(_StrictModel):
    job_id: JobId
    sample_id: SampleId
    sample_class: Literal["exome", "panel", "other"]
    variants: list[VariantCall]
    warnings: list[str] = Field(default_factory=list)


# ----- Analyzer -----


class CpicRecommendation(_StrictModel):
    drug: str = Field(min_length=1, max_length=64)
    recommendation: str = Field(min_length=1, max_length=1024)
    citation: str = Field(min_length=1, max_length=256)


class AnalyzerCall(_StrictModel):
    gene: str = Field(min_length=1, max_length=32)
    genotype: str = Field(min_length=1, max_length=64)
    phenotype: str = Field(min_length=1, max_length=64)
    cpic_recommendations: list[CpicRecommendation] = Field(default_factory=list)


class AnalyzerOutput(_StrictModel):
    job_id: JobId
    calls: list[AnalyzerCall] = Field(default_factory=list)


# ----- FHIR Composer -----


class FhirComposerOutput(_StrictModel):
    job_id: JobId
    bundle_s3_url: str = Field(pattern=S3_URL_PATTERN)
    resource_counts: dict[str, int]


# ----- Summarizer (Bedrock) -----


class SummarizerFinding(_StrictModel):
    gene: str = Field(min_length=1, max_length=32)
    phenotype: str = Field(min_length=1, max_length=64)
    drug: str = Field(min_length=1, max_length=64)


class SummarizerCitation(_StrictModel):
    source: Literal["CPIC", "DPWG"]
    guideline: str = Field(min_length=1, max_length=256)


class SummarizerOutput(_StrictModel):
    """Structured output expected from the Summarizer Bedrock call.

    Parsed and validated **before** anything is persisted to S3 or DynamoDB.
    """

    summary: str = Field(min_length=1, max_length=2048)
    key_findings: list[SummarizerFinding]
    citations: list[SummarizerCitation]
    confidence: float = Field(ge=0.0, le=1.0)


# ----- Critic (Bedrock + guardrails) -----


class CriticVerdict(_StrictModel):
    """Structured output from the Critic Bedrock call + guardrail checks."""

    verdict: Literal["approve", "reject"]
    reasons: list[FailureReason] = Field(default_factory=list)
    notes: str = Field(default="", max_length=1024)


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def utcnow() -> datetime:
    """Return a timezone-aware UTC datetime, used for record timestamps."""

    return datetime.now(tz=UTC)
