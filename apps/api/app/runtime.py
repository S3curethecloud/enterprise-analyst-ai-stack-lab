from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from apps.api.app.contracts import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisStatus,
    EvaluationResult,
    EvidenceItem,
    Finding,
    PolicyDecision,
    RuntimeMetadata,
    TraceRecord,
)
from apps.api.app.store import AnalysisStore
from apps.api.app.tracing import TraceRecorder


SUPPORTED_CAPABILITY = "customer-churn-analysis"


class DeterministicAnalystRuntime:
    def __init__(
        self,
        store: AnalysisStore,
        repository_root: Path | None = None,
    ) -> None:
        self.store = store
        self.repository_root = repository_root or Path(__file__).resolve().parents[3]

    async def execute(self, request: AnalysisRequest) -> AnalysisResult:
        if request.capability_id != SUPPORTED_CAPABILITY:
            raise ValueError(
                f"Unsupported capability_id: {request.capability_id}. "
                f"Supported capability: {SUPPORTED_CAPABILITY}."
            )

        analysis_id = f"ana_{uuid4().hex[:16]}"
        trace_id = f"trc_{uuid4().hex[:16]}"
        trace = TraceRecorder(trace_id)

        trace.add(
            "request.received",
            {
                "analysis_id": analysis_id,
                "capability_id": request.capability_id,
            },
        )

        trace.add(
            "identity.resolved",
            {
                "tenant_id": request.tenant_id,
                "workspace_id": request.workspace_id,
                "user_id": request.user_id,
            },
        )

        trace.add(
            "capability.selected",
            {
                "capability_id": request.capability_id,
                "capability_version": "phase-01-deterministic",
            },
        )

        trace.add(
            "context.plan.created",
            {
                "strategy": "phase-01-static-authorized-context",
                "required_sources": [
                    "customer-churn-snapshot",
                    "q2-support-summary",
                ],
            },
        )

        metrics = self._load_metrics()
        support_summary = self._load_support_summary()

        trace.add(
            "retrieval.executed",
            {
                "retrieved_source_ids": [
                    metrics["dataset_id"],
                    "q2-support-summary",
                ],
                "source_count": 2,
            },
        )

        trace.add(
            "tool.requested",
            {
                "tool_name": "query_customer_metrics",
                "side_effect": "none",
            },
        )

        policy_decision = PolicyDecision(
            decision="ALLOW",
            policy_id="phase-01-read-only-demo-policy",
            reasons=[
                "The request uses synthetic demonstration data.",
                "The requested tool is read-only.",
                "The tenant identifier matches the authorized demonstration tenant.",
            ],
        )

        trace.add(
            "policy.evaluated",
            policy_decision.model_dump(mode="json"),
        )

        trace.add(
            "tool.executed",
            {
                "tool_name": "query_customer_metrics",
                "result_dataset_id": metrics["dataset_id"],
                "status": "success",
            },
        )

        evidence = self._build_evidence(metrics, support_summary)

        trace.add(
            "context.compiled",
            {
                "evidence_ids": [item.source_id for item in evidence],
                "evidence_count": len(evidence),
                "context_strategy": "phase-01-static-authorized-context",
            },
        )

        trace.add(
            "model.simulated",
            {
                "execution_mode": "deterministic-simulation",
                "external_model_called": False,
            },
        )

        findings = self._build_findings(metrics)
        summary = self._build_summary(metrics)

        trace.add(
            "response.verified",
            {
                "schema_valid": True,
                "citation_count": sum(len(item.evidence_ids) for item in findings),
            },
        )

        evaluation = EvaluationResult(
            schema_valid=True,
            groundedness_score=1.0,
            evidence_coverage_score=1.0,
            policy_compliant=True,
            decision="PASS",
        )

        trace.add(
            "evaluation.completed",
            evaluation.model_dump(mode="json"),
        )

        trace.add(
            "response.returned",
            {
                "analysis_id": analysis_id,
                "status": AnalysisStatus.COMPLETED.value,
            },
        )

        trace.add(
            "evidence.bundle.created",
            {
                "analysis_id": analysis_id,
                "trace_id": trace_id,
            },
        )

        trace_record = trace.build()

        result = AnalysisResult(
            analysis_id=analysis_id,
            trace_id=trace_id,
            status=AnalysisStatus.COMPLETED,
            capability_id=request.capability_id,
            tenant_id=request.tenant_id,
            workspace_id=request.workspace_id,
            user_id=request.user_id,
            query=request.query,
            summary=summary,
            findings=findings,
            evidence=evidence,
            policy_decision=policy_decision,
            evaluation=evaluation,
            runtime=RuntimeMetadata(
                execution_mode="deterministic-simulation",
                context_strategy="phase-01-static-authorized-context",
                tool_calls=1,
                trace_event_count=trace.event_count,
            ),
        )

        self.store.save_analysis(result)
        self.store.save_trace(trace_record)
        self._persist_runtime_evidence(result, trace_record)

        return result

    def _load_metrics(self) -> dict:
        path = self.repository_root / "data/structured/customer_churn_snapshot.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_support_summary(self) -> str:
        path = self.repository_root / "data/documents/q2-support-summary.md"
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _build_evidence(metrics: dict, support_summary: str) -> list[EvidenceItem]:
        metric_values = metrics["metrics"]

        structured_excerpt = (
            f"Q2 churn was {metric_values['churn_rate']['current_percent']}%, "
            f"up {metric_values['churn_rate']['change_percentage_points']} percentage "
            f"points. Support incidents increased "
            f"{metric_values['support_incidents']['change_percent']}%, while weekly "
            f"active usage changed "
            f"{metric_values['weekly_active_usage']['change_percent']}%."
        )

        normalized_document = " ".join(support_summary.split())
        document_excerpt = normalized_document[:500]

        return [
            EvidenceItem(
                source_id=metrics["dataset_id"],
                source_type="structured-data",
                title="Synthetic Customer Churn Snapshot",
                excerpt=structured_excerpt,
                relevance_score=1.0,
            ),
            EvidenceItem(
                source_id="q2-support-summary",
                source_type="document",
                title="Q2 Synthetic Support Operations Summary",
                excerpt=document_excerpt,
                relevance_score=0.96,
            ),
            EvidenceItem(
                source_id="query-customer-metrics-result",
                source_type="tool-result",
                title="Customer Metrics Tool Result",
                excerpt=structured_excerpt,
                relevance_score=1.0,
            ),
        ]

    @staticmethod
    def _build_findings(metrics: dict) -> list[Finding]:
        values = metrics["metrics"]

        return [
            Finding(
                statement=(
                    "Customer churn increased by "
                    f"{values['churn_rate']['change_percentage_points']} percentage "
                    "points from Q1 to Q2."
                ),
                confidence=1.0,
                evidence_ids=[
                    metrics["dataset_id"],
                    "query-customer-metrics-result",
                ],
            ),
            Finding(
                statement=(
                    "Support incidents increased by "
                    f"{values['support_incidents']['change_percent']}%, creating a "
                    "strong operational signal associated with the churn increase."
                ),
                confidence=0.98,
                evidence_ids=[
                    metrics["dataset_id"],
                    "q2-support-summary",
                ],
            ),
            Finding(
                statement=(
                    "Weekly active product usage declined by "
                    f"{abs(values['weekly_active_usage']['change_percent'])}%, "
                    "indicating reduced engagement during the same period."
                ),
                confidence=0.98,
                evidence_ids=[
                    metrics["dataset_id"],
                    "q2-support-summary",
                ],
            ),
            Finding(
                statement=(
                    f"The highest-impact segment was {metrics['highest_impact_segment']}, "
                    "with incident concentration following the workflow migration."
                ),
                confidence=0.94,
                evidence_ids=[
                    metrics["dataset_id"],
                    "q2-support-summary",
                ],
            ),
        ]

    @staticmethod
    def _build_summary(metrics: dict) -> str:
        values = metrics["metrics"]

        return (
            f"Q2 churn increased from "
            f"{values['churn_rate']['previous_percent']}% to "
            f"{values['churn_rate']['current_percent']}%. The strongest contributing "
            f"signals were a {values['support_incidents']['change_percent']}% increase "
            f"in support incidents and a "
            f"{abs(values['weekly_active_usage']['change_percent'])}% reduction in "
            f"weekly active usage. The evidence indicates the greatest impact occurred "
            f"in the {metrics['highest_impact_segment']} segment following the April "
            "workflow migration. This conclusion is based exclusively on synthetic "
            "demonstration evidence."
        )

    def _persist_runtime_evidence(
        self,
        result: AnalysisResult,
        trace: TraceRecord,
    ) -> None:
        trace_directory = self.repository_root / "evidence/traces"
        policy_directory = self.repository_root / "evidence/policy-decisions"

        trace_directory.mkdir(parents=True, exist_ok=True)
        policy_directory.mkdir(parents=True, exist_ok=True)

        trace_path = trace_directory / f"{trace.trace_id}.json"
        policy_path = policy_directory / f"{trace.trace_id}.json"
        bundle_path = trace_directory / f"{result.analysis_id}-bundle.json"

        trace_path.write_text(
            json.dumps(trace.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        policy_path.write_text(
            json.dumps(result.policy_decision.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        bundle = {
            "analysis": result.model_dump(mode="json"),
            "trace": trace.model_dump(mode="json"),
            "policy_decision": result.policy_decision.model_dump(mode="json"),
            "evaluation": result.evaluation.model_dump(mode="json"),
        }

        bundle_path.write_text(
            json.dumps(bundle, indent=2),
            encoding="utf-8",
        )
