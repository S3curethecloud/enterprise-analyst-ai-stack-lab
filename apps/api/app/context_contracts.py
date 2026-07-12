from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class SourceType(str, Enum):
    STRUCTURED_DATA = "structured-data"
    DOCUMENT = "document"
    TOOL_RESULT = "tool-result"


class RetrievalMode(str, Enum):
    FAST = "fast"
    STANDARD = "standard"
    DEEP = "deep"


class ContextDecision(str, Enum):
    ALLOW = "ALLOW"
    RETURN_INSUFFICIENT_EVIDENCE = (
        "RETURN_INSUFFICIENT_EVIDENCE"
    )


class SourceMetadata(BaseModel):
    source_id: str = Field(min_length=1, max_length=256)
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_ids: list[str] = Field(min_length=1)
    classification: str = Field(min_length=1, max_length=128)
    source_type: SourceType
    title: str = Field(min_length=1, max_length=500)
    owner: str = Field(min_length=1, max_length=256)
    path: str = Field(min_length=1, max_length=1000)

    authoritative: bool = False

    created_at: datetime
    updated_at: datetime
    effective_at: datetime | None = None
    expires_at: datetime | None = None

    tags: list[str] = Field(default_factory=list)
    citation_uri: str | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> SourceMetadata:
        if self.updated_at < self.created_at:
            raise ValueError(
                "updated_at cannot be earlier than created_at"
            )

        if (
            self.expires_at is not None
            and self.effective_at is not None
            and self.expires_at <= self.effective_at
        ):
            raise ValueError(
                "expires_at must be later than effective_at"
            )

        return self


class SourceMetadataView(BaseModel):
    source_id: str
    tenant_id: str
    workspace_ids: list[str]
    classification: str
    source_type: SourceType
    title: str
    owner: str
    authoritative: bool

    created_at: datetime
    updated_at: datetime
    effective_at: datetime | None = None
    expires_at: datetime | None = None

    tags: list[str] = Field(default_factory=list)
    citation_uri: str | None = None


class SourceCatalogDocument(BaseModel):
    api_version: str = Field(
        pattern=r"^analyst\.securethecloud\.dev/v1$"
    )
    kind: str = Field(pattern=r"^SourceCatalog$")
    sources: list[SourceMetadata] = Field(min_length=1)


class ContextPolicy(BaseModel):
    api_version: str = Field(
        pattern=r"^analyst\.securethecloud\.dev/v1$"
    )
    kind: str = Field(pattern=r"^ContextPolicy$")

    policy_id: str = Field(min_length=1, max_length=128)
    mode: RetrievalMode

    allowed_source_types: list[SourceType] = Field(
        min_length=1
    )

    candidate_limit: int = Field(ge=1, le=1000)
    selected_limit: int = Field(ge=1, le=100)
    maximum_context_tokens: int = Field(
        ge=256,
        le=1_000_000,
    )

    minimum_relevance_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    minimum_sources: int = Field(ge=1, le=100)
    maximum_source_age_days: int | None = Field(
        default=None,
        ge=1,
    )

    require_authoritative_source: bool = False
    allow_expired_sources: bool = False

    @model_validator(mode="after")
    def validate_limits(self) -> ContextPolicy:
        if self.selected_limit > self.candidate_limit:
            raise ValueError(
                "selected_limit cannot exceed candidate_limit"
            )

        if self.minimum_sources > self.selected_limit:
            raise ValueError(
                "minimum_sources cannot exceed selected_limit"
            )

        return self


class InformationRequirement(BaseModel):
    requirement_id: str = Field(min_length=1, max_length=128)
    topic: str = Field(min_length=1, max_length=500)
    required_terms: list[str] = Field(default_factory=list)
    priority: int = Field(ge=1, le=5)


class RetrievalRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=128)
    workspace_id: str = Field(min_length=1, max_length=128)
    query: str = Field(min_length=1, max_length=4000)

    capability_id: str = Field(min_length=1, max_length=128)
    context_policy_id: str = Field(
        min_length=1,
        max_length=128,
    )

    allowed_classifications: list[str] = Field(min_length=1)
    requirements: list[InformationRequirement] = Field(
        min_length=1
    )


class SourceDocument(BaseModel):
    metadata: SourceMetadata
    content: str = Field(min_length=1)
    structured_payload: dict[str, Any] | None = None
    content_hash: str
    estimated_tokens: int = Field(ge=1)


class RetrievalCandidate(BaseModel):
    document: SourceDocument

    lexical_score: float = Field(ge=0.0, le=1.0)
    metadata_score: float = Field(ge=0.0, le=1.0)
    freshness_score: float = Field(ge=0.0, le=1.0)
    authority_score: float = Field(ge=0.0, le=1.0)
    total_score: float = Field(ge=0.0, le=1.0)

    matched_requirements: list[str] = Field(
        default_factory=list
    )


class ContextItem(BaseModel):
    source_id: str
    source_type: SourceType
    title: str
    content: str
    structured_payload: dict[str, Any] | None = None

    relevance_score: float = Field(ge=0.0, le=1.0)
    estimated_tokens: int = Field(ge=1)

    tenant_id: str
    classification: str
    authoritative: bool
    updated_at: datetime

    content_hash: str
    citation_uri: str | None = None
    matched_requirements: list[str] = Field(
        default_factory=list
    )


class ContextPackage(BaseModel):
    package_id: str
    decision: ContextDecision

    capability_id: str
    policy_id: str
    retrieval_mode: RetrievalMode

    items: list[ContextItem]
    total_tokens: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    selected_count: int = Field(ge=0)

    covered_requirements: list[str] = Field(
        default_factory=list
    )
    missing_requirements: list[str] = Field(
        default_factory=list
    )
    decision_reasons: list[str] = Field(
        default_factory=list
    )
