"""Shared utilities used by every Lambda in the service.

Re-exports the most commonly-imported names so individual Lambdas can
write::

    from service.common import (
        SubmitJobRequest,
        get_logger,
        ServiceError,
        to_api_response,
    )

Larger imports (full enums, agent I/O records) can be pulled directly
from ``service.common.models``.
"""

from service.common.errors import (
    JobNotReadyError,
    NotFoundError,
    PipelineError,
    ServiceError,
    UpstreamError,
    ValidationError,
    to_api_response,
)
from service.common.logging import JsonFormatter, get_logger
from service.common.models import (
    AgentName,
    AgentRunRecord,
    AnalyzerCall,
    AnalyzerOutput,
    AuditRecord,
    CorrelationId,
    CpicRecommendation,
    CriticVerdict,
    FailureReason,
    FhirComposerOutput,
    GetJobResponse,
    GetReportResponse,
    IntakeOutput,
    JobId,
    JobRecord,
    JobStatus,
    PipelineEvent,
    SampleId,
    SubmitJobRequest,
    SubmitJobResponse,
    SummarizerCitation,
    SummarizerFinding,
    SummarizerOutput,
    VariantCall,
    utcnow,
)

__all__ = [
    "AgentName",
    "AgentRunRecord",
    "AnalyzerCall",
    "AnalyzerOutput",
    "AuditRecord",
    "CorrelationId",
    "CpicRecommendation",
    "CriticVerdict",
    "FailureReason",
    "FhirComposerOutput",
    "GetJobResponse",
    "GetReportResponse",
    "IntakeOutput",
    "JobId",
    "JobNotReadyError",
    "JobRecord",
    "JobStatus",
    "JsonFormatter",
    "NotFoundError",
    "PipelineError",
    "PipelineEvent",
    "SampleId",
    "ServiceError",
    "SubmitJobRequest",
    "SubmitJobResponse",
    "SummarizerCitation",
    "SummarizerFinding",
    "SummarizerOutput",
    "UpstreamError",
    "ValidationError",
    "VariantCall",
    "get_logger",
    "to_api_response",
    "utcnow",
]
