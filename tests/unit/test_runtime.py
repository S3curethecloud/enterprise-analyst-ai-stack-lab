import asyncio

import pytest

from apps.api.app.contracts import AnalysisRequest, AnalysisStatus
from apps.api.app.runtime import DeterministicAnalystRuntime
from apps.api.app.store import AnalysisStore


def build_request(capability_id: str = "customer-churn-analysis") -> AnalysisRequest:
    return AnalysisRequest(
        tenant_id="tenant-demo",
        workspace_id="workspace-customer-intelligence",
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
    assert len(result.findings) == 4
    assert len(result.evidence) == 3


def test_runtime_rejects_unsupported_capability() -> None:
    runtime = DeterministicAnalystRuntime(store=AnalysisStore())

    with pytest.raises(ValueError, match="Unsupported capability_id"):
        asyncio.run(
            runtime.execute(
                build_request(capability_id="unregistered-capability")
            )
        )
