from pathlib import Path

import pytest
import yaml

from apps.api.app.context_contracts import RetrievalMode
from apps.api.app.context_registry import (
    ContextPolicyRegistry,
    ContextRegistryError,
    SourceCatalog,
)


ROOT = Path(__file__).resolve().parents[2]


def test_repository_context_policies_are_valid() -> None:
    registry = ContextPolicyRegistry(
        ROOT / "context-policies"
    ).load()

    policies = registry.list_all()

    assert len(policies) == 3

    assert {
        policy.policy_id
        for policy in policies
    } == {
        "churn-fast-v1",
        "churn-standard-v1",
        "churn-deep-v1",
    }

    standard = registry.get("churn-standard-v1")

    assert standard.mode == RetrievalMode.STANDARD
    assert standard.minimum_sources == 2
    assert standard.maximum_context_tokens == 5000
    assert standard.require_authoritative_source is True


def test_repository_source_catalog_is_valid() -> None:
    catalog = SourceCatalog(
        catalog_path=ROOT / "data/metadata/sources.yaml",
        repository_root=ROOT,
    ).load()

    sources = catalog.list_all()

    assert len(sources) == 2

    churn_source = catalog.get(
        "customer-churn-snapshot-2026-q2"
    )

    assert churn_source.tenant_id == "tenant-demo"
    assert churn_source.authoritative is True
    assert churn_source.classification == (
        "synthetic-internal"
    )
    assert (
        "workspace-customer-intelligence"
        in churn_source.workspace_ids
    )


def test_duplicate_policy_id_is_rejected(
    tmp_path: Path,
) -> None:
    payload = {
        "api_version": "analyst.securethecloud.dev/v1",
        "kind": "ContextPolicy",
        "policy_id": "duplicate-policy",
        "mode": "fast",
        "allowed_source_types": ["document"],
        "candidate_limit": 2,
        "selected_limit": 1,
        "maximum_context_tokens": 500,
        "minimum_relevance_score": 0.5,
        "minimum_sources": 1,
        "require_authoritative_source": False,
        "allow_expired_sources": False,
    }

    for filename in ("one.yaml", "two.yaml"):
        (tmp_path / filename).write_text(
            yaml.safe_dump(payload),
            encoding="utf-8",
        )

    with pytest.raises(
        ContextRegistryError,
        match="Duplicate context policy ID",
    ):
        ContextPolicyRegistry(tmp_path).load()


def test_missing_source_path_is_rejected(
    tmp_path: Path,
) -> None:
    catalog_path = tmp_path / "sources.yaml"

    payload = {
        "api_version": "analyst.securethecloud.dev/v1",
        "kind": "SourceCatalog",
        "sources": [
            {
                "source_id": "missing-source",
                "tenant_id": "tenant-demo",
                "workspace_ids": ["workspace-demo"],
                "classification": "synthetic-internal",
                "source_type": "document",
                "title": "Missing source",
                "owner": "test-owner",
                "path": "data/documents/missing.md",
                "authoritative": False,
                "created_at": "2026-07-01T00:00:00Z",
                "updated_at": "2026-07-01T00:00:00Z",
                "tags": [],
            }
        ],
    }

    catalog_path.write_text(
        yaml.safe_dump(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        ContextRegistryError,
        match="Source path does not exist",
    ):
        SourceCatalog(
            catalog_path=catalog_path,
            repository_root=tmp_path,
        ).load()
