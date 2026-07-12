from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from apps.api.app.context_contracts import (
    ContextDecision,
    RetrievalRequest,
)
from apps.api.app.context_engine import (
    GovernedContextEngine,
    InformationRequirementPlanner,
)
from apps.api.app.context_registry import (
    ContextPolicyRegistry,
    SourceCatalog,
)
from apps.api.app.retrieval_adapters import (
    SourceDocumentLoader,
)


ROOT = Path(__file__).resolve().parents[2]

FIXED_NOW = datetime(
    2026,
    7,
    12,
    12,
    0,
    0,
    tzinfo=timezone.utc,
)


def build_repository_engine() -> GovernedContextEngine:
    return GovernedContextEngine(
        source_catalog=SourceCatalog(
            catalog_path=(
                ROOT / "data/metadata/sources.yaml"
            ),
            repository_root=ROOT,
        ).load(),
        policy_registry=ContextPolicyRegistry(
            ROOT / "context-policies"
        ).load(),
        source_loader=SourceDocumentLoader(ROOT),
    )


def build_request(
    tenant_id: str = "tenant-demo",
    workspace_id: str = (
        "workspace-customer-intelligence"
    ),
    classification: str = "synthetic-internal",
    policy_id: str = "churn-standard-v1",
    query: str = (
        "Explain why customer churn increased during Q2. "
        "Compare support incidents and product usage."
    ),
    capability_id: str = "customer-churn-analysis",
) -> RetrievalRequest:
    planner = InformationRequirementPlanner()

    return RetrievalRequest(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        query=query,
        capability_id=capability_id,
        context_policy_id=policy_id,
        allowed_classifications=[classification],
        requirements=planner.plan(
            query=query,
            capability_id=capability_id,
        ),
    )


def test_planner_creates_churn_requirements() -> None:
    planner = InformationRequirementPlanner()

    requirements = planner.plan(
        query="Explain the Q2 churn increase.",
        capability_id="customer-churn-analysis",
    )

    assert {
        item.requirement_id
        for item in requirements
    } == {
        "churn-change",
        "support-signal",
        "usage-signal",
    }


def test_standard_context_returns_authorized_evidence() -> None:
    engine = build_repository_engine()

    package = engine.build_context(
        build_request(),
        now=FIXED_NOW,
    )

    assert package.decision == ContextDecision.ALLOW
    assert package.policy_id == "churn-standard-v1"
    assert package.selected_count == 2
    assert package.total_tokens <= 5000
    assert package.missing_requirements == []

    assert {
        item.source_id
        for item in package.items
    } == {
        "customer-churn-snapshot-2026-q2",
        "q2-support-summary",
    }

    assert all(
        item.tenant_id == "tenant-demo"
        for item in package.items
    )

    assert all(
        item.citation_uri is not None
        for item in package.items
    )

    assert any(
        item.authoritative
        for item in package.items
    )


def test_cross_tenant_retrieval_is_blocked() -> None:
    engine = build_repository_engine()

    package = engine.build_context(
        build_request(tenant_id="tenant-other"),
        now=FIXED_NOW,
    )

    assert package.decision == (
        ContextDecision.RETURN_INSUFFICIENT_EVIDENCE
    )

    assert package.selected_count == 0
    assert package.items == []


def test_workspace_isolation_is_enforced() -> None:
    engine = build_repository_engine()

    package = engine.build_context(
        build_request(
            workspace_id="workspace-unauthorized"
        ),
        now=FIXED_NOW,
    )

    assert package.decision == (
        ContextDecision.RETURN_INSUFFICIENT_EVIDENCE
    )

    assert package.selected_count == 0


def test_classification_filter_is_enforced() -> None:
    engine = build_repository_engine()

    package = engine.build_context(
        build_request(
            classification="public"
        ),
        now=FIXED_NOW,
    )

    assert package.decision == (
        ContextDecision.RETURN_INSUFFICIENT_EVIDENCE
    )

    assert package.selected_count == 0


def test_context_modes_respect_token_budgets() -> None:
    engine = build_repository_engine()

    expectations = {
        "churn-fast-v1": 1800,
        "churn-standard-v1": 5000,
        "churn-deep-v1": 10000,
    }

    for policy_id, token_limit in expectations.items():
        package = engine.build_context(
            build_request(policy_id=policy_id),
            now=FIXED_NOW,
        )

        assert package.total_tokens <= token_limit
        assert package.selected_count <= 10


def test_irrelevant_information_need_is_insufficient() -> None:
    engine = build_repository_engine()

    request = build_request(
        query=(
            "Analyze annual office lease pricing and "
            "commercial property tax exposure."
        ),
        capability_id="generic-analysis",
    )

    package = engine.build_context(
        request,
        now=FIXED_NOW,
    )

    assert package.decision == (
        ContextDecision.RETURN_INSUFFICIENT_EVIDENCE
    )

    assert package.missing_requirements == [
        "primary-information-need"
    ]


def test_duplicate_content_is_deduplicated(
    tmp_path: Path,
) -> None:
    document_directory = tmp_path / "data/documents"
    metadata_directory = tmp_path / "data/metadata"
    policy_directory = tmp_path / "context-policies"

    document_directory.mkdir(parents=True)
    metadata_directory.mkdir(parents=True)
    policy_directory.mkdir(parents=True)

    shared_content = (
        "Support incidents increased after the migration."
    )

    first_path = document_directory / "one.md"
    second_path = document_directory / "two.md"

    first_path.write_text(
        shared_content,
        encoding="utf-8",
    )
    second_path.write_text(
        shared_content,
        encoding="utf-8",
    )

    catalog = {
        "api_version": "analyst.securethecloud.dev/v1",
        "kind": "SourceCatalog",
        "sources": [],
    }

    for source_id, relative_path in (
        ("source-one", "data/documents/one.md"),
        ("source-two", "data/documents/two.md"),
    ):
        catalog["sources"].append(
            {
                "source_id": source_id,
                "tenant_id": "tenant-demo",
                "workspace_ids": ["workspace-demo"],
                "classification": "synthetic-internal",
                "source_type": "document",
                "title": "Support incident summary",
                "owner": "operations",
                "path": relative_path,
                "authoritative": True,
                "created_at": "2026-07-01T00:00:00Z",
                "updated_at": "2026-07-01T00:00:00Z",
                "tags": [
                    "support",
                    "incident",
                    "migration",
                ],
            }
        )

    (metadata_directory / "sources.yaml").write_text(
        yaml.safe_dump(
            catalog,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    policy = {
        "api_version": "analyst.securethecloud.dev/v1",
        "kind": "ContextPolicy",
        "policy_id": "test-policy",
        "mode": "standard",
        "allowed_source_types": ["document"],
        "candidate_limit": 10,
        "selected_limit": 5,
        "maximum_context_tokens": 1000,
        "minimum_relevance_score": 0.1,
        "minimum_sources": 1,
        "maximum_source_age_days": 365,
        "require_authoritative_source": True,
        "allow_expired_sources": False,
    }

    (policy_directory / "test-policy.yaml").write_text(
        yaml.safe_dump(
            policy,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    engine = GovernedContextEngine(
        source_catalog=SourceCatalog(
            catalog_path=(
                metadata_directory / "sources.yaml"
            ),
            repository_root=tmp_path,
        ).load(),
        policy_registry=ContextPolicyRegistry(
            policy_directory
        ).load(),
        source_loader=SourceDocumentLoader(tmp_path),
    )

    planner = InformationRequirementPlanner()
    query = "Analyze support incidents after migration."

    request = RetrievalRequest(
        tenant_id="tenant-demo",
        workspace_id="workspace-demo",
        query=query,
        capability_id="generic-analysis",
        context_policy_id="test-policy",
        allowed_classifications=[
            "synthetic-internal"
        ],
        requirements=planner.plan(
            query=query,
            capability_id="generic-analysis",
        ),
    )

    package = engine.build_context(
        request=request,
        now=FIXED_NOW,
    )

    assert package.decision == ContextDecision.ALLOW
    assert package.candidate_count == 1
    assert package.selected_count == 1
