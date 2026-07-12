from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import uuid4

from apps.api.app.context_contracts import (
    ContextDecision,
    ContextItem,
    ContextPackage,
    ContextPolicy,
    InformationRequirement,
    RetrievalCandidate,
    RetrievalMode,
    RetrievalRequest,
    SourceDocument,
    SourceMetadata,
)
from apps.api.app.context_registry import (
    ContextPolicyRegistry,
    SourceCatalog,
)
from apps.api.app.retrieval_adapters import (
    SourceDocumentLoader,
)


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "during",
    "explain",
    "for",
    "from",
    "give",
    "in",
    "is",
    "it",
    "of",
    "on",
    "provide",
    "the",
    "then",
    "to",
    "was",
    "what",
    "why",
    "with",
}


def tokenize(value: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(
            r"[a-z0-9]+",
            value.lower(),
        )
        if token not in STOP_WORDS
    }

    return tokens


class InformationRequirementPlanner:
    def plan(
        self,
        query: str,
        capability_id: str,
    ) -> list[InformationRequirement]:
        if capability_id == "customer-churn-analysis":
            return [
                InformationRequirement(
                    requirement_id="churn-change",
                    topic="Measured change in customer churn",
                    required_terms=[
                        "churn",
                        "rate",
                        "increase",
                        "q1",
                        "q2",
                    ],
                    priority=5,
                ),
                InformationRequirement(
                    requirement_id="support-signal",
                    topic="Support incident trend",
                    required_terms=[
                        "support",
                        "incident",
                        "migration",
                        "authentication",
                    ],
                    priority=4,
                ),
                InformationRequirement(
                    requirement_id="usage-signal",
                    topic="Product usage and engagement trend",
                    required_terms=[
                        "product",
                        "usage",
                        "active",
                        "engagement",
                    ],
                    priority=4,
                ),
            ]

        query_terms = sorted(tokenize(query))

        if not query_terms:
            query_terms = ["requested", "analysis"]

        return [
            InformationRequirement(
                requirement_id="primary-information-need",
                topic=query,
                required_terms=query_terms[:12],
                priority=5,
            )
        ]


class GovernedContextEngine:
    def __init__(
        self,
        source_catalog: SourceCatalog,
        policy_registry: ContextPolicyRegistry,
        source_loader: SourceDocumentLoader,
    ) -> None:
        self.source_catalog = source_catalog
        self.policy_registry = policy_registry
        self.source_loader = source_loader

    def build_context(
        self,
        request: RetrievalRequest,
        now: datetime | None = None,
    ) -> ContextPackage:
        current_time = now or datetime.now(timezone.utc)
        policy = self.policy_registry.get(
            request.context_policy_id
        )

        candidates: list[RetrievalCandidate] = []

        for metadata in self.source_catalog.list_all():
            if not self._source_is_allowed(
                metadata=metadata,
                request=request,
                policy=policy,
                now=current_time,
            ):
                continue

            document = self.source_loader.load(metadata)

            candidate = self._score_document(
                document=document,
                request=request,
                policy=policy,
                now=current_time,
            )

            candidates.append(candidate)

        deduplicated = self._deduplicate(candidates)

        ranked = sorted(
            deduplicated,
            key=lambda item: (
                item.total_score,
                item.authority_score,
                item.freshness_score,
                item.document.metadata.source_id,
            ),
            reverse=True,
        )[: policy.candidate_limit]

        eligible = [
            candidate
            for candidate in ranked
            if candidate.total_score
            >= policy.minimum_relevance_score
        ]

        selected: list[RetrievalCandidate] = []
        total_tokens = 0

        for candidate in eligible:
            if len(selected) >= policy.selected_limit:
                break

            candidate_tokens = (
                candidate.document.estimated_tokens
            )

            if (
                total_tokens + candidate_tokens
                > policy.maximum_context_tokens
            ):
                continue

            selected.append(candidate)
            total_tokens += candidate_tokens

        covered_requirements = sorted(
            {
                requirement_id
                for candidate in selected
                for requirement_id
                in candidate.matched_requirements
            }
        )

        requested_requirement_ids = {
            requirement.requirement_id
            for requirement in request.requirements
        }

        missing_requirements = sorted(
            requested_requirement_ids
            - set(covered_requirements)
        )

        reasons: list[str] = []

        if len(selected) < policy.minimum_sources:
            reasons.append(
                "The selected evidence count is below the "
                f"policy minimum of {policy.minimum_sources}."
            )

        if missing_requirements:
            reasons.append(
                "The retrieved context does not cover all "
                "information requirements."
            )

        if (
            policy.require_authoritative_source
            and not any(
                candidate.document.metadata.authoritative
                for candidate in selected
            )
        ):
            reasons.append(
                "The policy requires at least one authoritative "
                "source."
            )

        decision = ContextDecision.ALLOW

        if reasons:
            decision = (
                ContextDecision.RETURN_INSUFFICIENT_EVIDENCE
            )

        items = [
            self._to_context_item(candidate)
            for candidate in selected
        ]

        return ContextPackage(
            package_id=f"ctx_{uuid4().hex[:16]}",
            decision=decision,
            capability_id=request.capability_id,
            policy_id=policy.policy_id,
            retrieval_mode=policy.mode,
            items=items,
            total_tokens=total_tokens,
            candidate_count=len(ranked),
            selected_count=len(items),
            covered_requirements=covered_requirements,
            missing_requirements=missing_requirements,
            decision_reasons=reasons,
        )

    @staticmethod
    def _source_is_allowed(
        metadata: SourceMetadata,
        request: RetrievalRequest,
        policy: ContextPolicy,
        now: datetime,
    ) -> bool:
        if metadata.tenant_id != request.tenant_id:
            return False

        if request.workspace_id not in metadata.workspace_ids:
            return False

        if (
            metadata.classification
            not in request.allowed_classifications
        ):
            return False

        if (
            metadata.source_type
            not in policy.allowed_source_types
        ):
            return False

        if (
            metadata.effective_at is not None
            and metadata.effective_at > now
        ):
            return False

        if (
            metadata.expires_at is not None
            and metadata.expires_at <= now
            and not policy.allow_expired_sources
        ):
            return False

        if policy.maximum_source_age_days is not None:
            age_days = max(
                0,
                (now - metadata.updated_at).days,
            )

            if age_days > policy.maximum_source_age_days:
                return False

        return True

    @staticmethod
    def _score_document(
        document: SourceDocument,
        request: RetrievalRequest,
        policy: ContextPolicy,
        now: datetime,
    ) -> RetrievalCandidate:
        metadata = document.metadata

        query_tokens = tokenize(request.query)

        requirement_tokens = {
            token
            for requirement in request.requirements
            for term in requirement.required_terms
            for token in tokenize(term)
        }

        target_tokens = query_tokens | requirement_tokens

        content_tokens = tokenize(
            " ".join(
                [
                    metadata.title,
                    document.content,
                    " ".join(metadata.tags),
                ]
            )
        )

        lexical_overlap = target_tokens & content_tokens

        lexical_score = (
            len(lexical_overlap) / len(target_tokens)
            if target_tokens
            else 0.0
        )

        metadata_tokens = tokenize(
            " ".join(
                [
                    metadata.title,
                    " ".join(metadata.tags),
                    metadata.owner,
                ]
            )
        )

        metadata_overlap = target_tokens & metadata_tokens

        metadata_score = (
            len(metadata_overlap) / len(target_tokens)
            if target_tokens
            else 0.0
        )

        freshness_score = (
            GovernedContextEngine._freshness_score(
                metadata=metadata,
                policy=policy,
                now=now,
            )
        )

        authority_score = (
            1.0 if metadata.authoritative else 0.4
        )

        weights = {
            RetrievalMode.FAST: (
                0.55,
                0.25,
                0.10,
                0.10,
            ),
            RetrievalMode.STANDARD: (
                0.45,
                0.25,
                0.15,
                0.15,
            ),
            RetrievalMode.DEEP: (
                0.40,
                0.25,
                0.15,
                0.20,
            ),
        }[policy.mode]

        total_score = min(
            1.0,
            (
                lexical_score * weights[0]
                + metadata_score * weights[1]
                + freshness_score * weights[2]
                + authority_score * weights[3]
            ),
        )

        matched_requirements: list[str] = []

        for requirement in request.requirements:
            required_tokens = {
                token
                for term in requirement.required_terms
                for token in tokenize(term)
            }

            if not required_tokens:
                continue

            overlap = required_tokens & content_tokens
            coverage = len(overlap) / len(required_tokens)

            if coverage >= 0.20:
                matched_requirements.append(
                    requirement.requirement_id
                )

        return RetrievalCandidate(
            document=document,
            lexical_score=round(lexical_score, 6),
            metadata_score=round(metadata_score, 6),
            freshness_score=round(freshness_score, 6),
            authority_score=authority_score,
            total_score=round(total_score, 6),
            matched_requirements=sorted(
                matched_requirements
            ),
        )

    @staticmethod
    def _freshness_score(
        metadata: SourceMetadata,
        policy: ContextPolicy,
        now: datetime,
    ) -> float:
        if policy.maximum_source_age_days is None:
            return 1.0

        age_days = max(
            0,
            (now - metadata.updated_at).days,
        )

        return max(
            0.0,
            1.0
            - (
                age_days
                / policy.maximum_source_age_days
            ),
        )

    @staticmethod
    def _deduplicate(
        candidates: list[RetrievalCandidate],
    ) -> list[RetrievalCandidate]:
        by_hash: dict[str, RetrievalCandidate] = {}

        for candidate in candidates:
            content_hash = (
                candidate.document.content_hash
            )

            existing = by_hash.get(content_hash)

            if (
                existing is None
                or candidate.total_score
                > existing.total_score
            ):
                by_hash[content_hash] = candidate

        return list(by_hash.values())

    @staticmethod
    def _to_context_item(
        candidate: RetrievalCandidate,
    ) -> ContextItem:
        metadata = candidate.document.metadata

        return ContextItem(
            source_id=metadata.source_id,
            source_type=metadata.source_type,
            title=metadata.title,
            content=candidate.document.content,
            structured_payload=(
                candidate.document.structured_payload
            ),
            relevance_score=candidate.total_score,
            estimated_tokens=(
                candidate.document.estimated_tokens
            ),
            tenant_id=metadata.tenant_id,
            classification=metadata.classification,
            authoritative=metadata.authoritative,
            updated_at=metadata.updated_at,
            content_hash=(
                candidate.document.content_hash
            ),
            citation_uri=metadata.citation_uri,
            matched_requirements=(
                candidate.matched_requirements
            ),
        )
