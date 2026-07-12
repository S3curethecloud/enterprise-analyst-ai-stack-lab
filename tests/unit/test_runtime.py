import asyncio

import pytest

from apps.api.app.contracts import AnalysisRequest, AnalysisStatus
from apps.api.app.runtime import DeterministicAnalystRuntime
from apps.api.app.store import AnalysisStore


def build_request(
    capability_id: str = "customer-churn-analysis",
    tenant_id: str = "tenant-demo",
    workspace_id: str = "workspace-customer-intelligence",
) -> AnalysisRequest:
    return AnalysisRequest(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        user_id="analyst-001",
        capability_id=capability_id,
        query=(
            "Explain why customer churn increased during Q2 and provide "
            "an evidence-backed executive summary."
        ),
    )


def test_deterministic_runtime_produces_grounded_result() -> None:
    runtime = DeterministicAnalystRuntime(store=AnalysisStore())

    result = asyncio.run(runtime.execute(build_request()))

    assert result.status == AnalysisStatus.COMPLETED
    assert result.capability_id == "customer-churn-analysis"
    assert result.evaluation.decision == "PASS"
    assert result.evaluation.schema_valid is True
    assert result.evaluation.groundedness_score == 1.0
    assert result.policy_decision.decision == "ALLOW"
    assert result.runtime.execution_mode == "deterministic-simulation"
    assert result.runtime.tool_calls == 1
    assert result.runtime.trace_event_count >= 10

    assert result.runtime.context_package_id is not None
    assert result.runtime.context_package_id.startswith(
        "ctx_"
    )
    assert result.runtime.retrieval_mode == "standard"
    assert (
        result.runtime.retrieval_candidate_count
        == 2
    )
    assert (
        result.runtime.retrieval_selected_count
        == 2
    )
    assert result.runtime.context_tokens > 0

    assert len(result.findings) == 4
    assert len(result.evidence) == 3

    retrieved_evidence = [
        item
        for item in result.evidence
        if item.source_type != "tool-result"
    ]

    assert len(retrieved_evidence) == 2

    assert all(
        item.tenant_id == "tenant-demo"
        for item in retrieved_evidence
    )

    assert all(
        item.classification
        == "synthetic-internal"
        for item in retrieved_evidence
    )

    assert all(
        item.authoritative is True
        for item in retrieved_evidence
    )

    assert all(
        item.content_hash is not None
        for item in retrieved_evidence
    )

    assert all(
        item.citation_uri is not None
        for item in retrieved_evidence
    )

    assert {
        item.source_id
        for item in retrieved_evidence
    } == {
        "customer-churn-snapshot-2026-q2",
        "q2-support-summary",
    }


def test_runtime_rejects_unsupported_capability() -> None:
    runtime = DeterministicAnalystRuntime(store=AnalysisStore())

    with pytest.raises(ValueError, match="Capability not found"):
        asyncio.run(
            runtime.execute(
                build_request(capability_id="unregistered-capability")
            )
        )


def test_runtime_stops_when_tenant_has_no_authorized_context() -> None:
    runtime = DeterministicAnalystRuntime(
        store=AnalysisStore()
    )

    result = asyncio.run(
        runtime.execute(
            build_request(
                tenant_id="tenant-other"
            )
        )
    )

    assert result.status == AnalysisStatus.COMPLETED

    assert result.policy_decision.decision == (
        "RETURN_INSUFFICIENT_EVIDENCE"
    )

    assert result.policy_decision.policy_id == (
        "churn-standard-v1"
    )

    assert result.evaluation.decision == "REVIEW"
    assert result.evaluation.schema_valid is True
    assert result.evaluation.policy_compliant is True
    assert (
        result.evaluation.evidence_coverage_score
        == 0.0
    )

    assert result.runtime.context_package_id is not None
    assert result.runtime.context_package_id.startswith(
        "ctx_"
    )
    assert result.runtime.retrieval_mode == "standard"
    assert (
        result.runtime.retrieval_candidate_count
        == 0
    )
    assert (
        result.runtime.retrieval_selected_count
        == 0
    )
    assert result.runtime.context_tokens == 0
    assert result.runtime.tool_calls == 0

    assert result.findings == []
    assert result.evidence == []

    assert "not executed" in result.summary
    assert "sufficient authorized evidence" in (
        result.summary
    )
