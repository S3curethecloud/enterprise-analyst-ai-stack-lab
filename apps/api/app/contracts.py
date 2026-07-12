from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AnalysisRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    user_id: str = Field(min_length=1, max_length=128)
    query: str = Field(min_length=10, max_length=4000)
    capability_id: str = Field(
        default="customer-churn-analysis",
        min_length=1,
        max_length=128,
    )


class EvidenceItem(BaseModel):
    source_id: str
    source_type: Literal["structured-data", "document", "tool-result"]
    title: str
    excerpt: str
    relevance_score: float = Field(ge=0.0, le=1.0)


class Finding(BaseModel):
    statement: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_ids: list[str]


class PolicyDecision(BaseModel):
    decision: Literal[
        "ALLOW",
        "DENY",
        "REDACT",
        "REQUIRE_APPROVAL",
        "RETRY_WITH_RESTRICTED_CONTEXT",
        "RETURN_INSUFFICIENT_EVIDENCE",
        "ESCALATE_TO_HUMAN",
    ]
    policy_id: str
    reasons: list[str]


class EvaluationResult(BaseModel):
    schema_valid: bool
    groundedness_score: float = Field(ge=0.0, le=1.0)
    evidence_coverage_score: float = Field(ge=0.0, le=1.0)
    policy_compliant: bool
    decision: Literal["PASS", "FAIL", "REVIEW"]


class RuntimeMetadata(BaseModel):
    execution_mode: str
    context_strategy: str
    tool_calls: int = Field(ge=0)
    trace_event_count: int = Field(ge=0)


class AnalysisResult(BaseModel):
    analysis_id: str
    trace_id: str
    status: AnalysisStatus
    capability_id: str
    tenant_id: str
    workspace_id: str
    user_id: str
    query: str
    summary: str
    findings: list[Finding]
    evidence: list[EvidenceItem]
    policy_decision: PolicyDecision
    evaluation: EvaluationResult
    runtime: RuntimeMetadata
    created_at: datetime = Field(default_factory=utc_now)


class TraceEvent(BaseModel):
    sequence: int = Field(ge=1)
    event_type: str
    timestamp: datetime = Field(default_factory=utc_now)
    details: dict[str, Any] = Field(default_factory=dict)


class TraceRecord(BaseModel):
    trace_id: str
    events: list[TraceEvent]


class HealthResponse(BaseModel):
    status: Literal["healthy"]
    service: str
    version: str
    execution_mode: str
