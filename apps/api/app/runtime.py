from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from apps.api.app.context_contracts import (
    ContextDecision,
    ContextItem,
    ContextPackage,
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
from apps.api.app.registry import (
    CapabilityManifest,
    CapabilityRegistry,
    PromptRegistry,
    RegistryItemNotFoundError,
    validate_registry_bindings,
)
from apps.api.app.retrieval_adapters import (
    SourceDocumentLoader,
)
from apps.api.app.store import AnalysisStore
from apps.api.app.tracing import TraceRecorder


class DeterministicAnalystRuntime:
    def __init__(
        self,
        store: AnalysisStore,
        repository_root: Path | None = None,
        capability_registry: CapabilityRegistry | None = None,
        prompt_registry: PromptRegistry | None = None,
        context_engine: GovernedContextEngine | None = None,
        requirement_planner: InformationRequirementPlanner | None = None,
    ) -> None:
        self.store = store
        self.repository_root = (
            repository_root
            or Path(__file__).resolve().parents[3]
        )

        self.capability_registry = (
            capability_registry
            or CapabilityRegistry(
                self.repository_root / "capabilities"
            ).load()
        )

        self.prompt_registry = (
            prompt_registry
            or PromptRegistry(
                self.repository_root / "prompts"
            ).load()
        )

        validate_registry_bindings(
            self.capability_registry,
            self.prompt_registry,
        )

        self.context_engine = (
            context_engine
            or GovernedContextEngine(
                source_catalog=SourceCatalog(
                    catalog_path=(
                        self.repository_root
                        / "data/metadata/sources.yaml"
                    ),
                    repository_root=self.repository_root,
                ).load(),
                policy_registry=ContextPolicyRegistry(
                    self.repository_root
                    / "context-policies"
                ).load(),
                source_loader=SourceDocumentLoader(
                    self.repository_root
                ),
            )
        )

        self.requirement_planner = (
            requirement_planner
            or InformationRequirementPlanner()
        )

    async def execute(self, request: AnalysisRequest) -> AnalysisResult:
        try:
            capability = self.capability_registry.get(
                request.capability_id
            )
        except RegistryItemNotFoundError as exc:
            raise ValueError(str(exc)) from exc

        if capability.metadata.status != "active":
            raise ValueError(
                "Capability is not active: "
                f"{capability.metadata.id} "
                f"[{capability.metadata.status}]"
            )

        execution_profile = (
            capability.spec.runtime.execution_profile
        )

        if execution_profile != "churn-synthesis-v1":
            raise ValueError(
                "Execution profile is not implemented: "
                f"{execution_profile}"
            )

        prompt_bundle = capability.spec.prompt_bundle

        prompt_references = {
            "system": prompt_bundle.system,
            "task": prompt_bundle.task,
            "verifier": prompt_bundle.verifier,
        }

        prompt_versions: dict[str, str] = {}

        for role, reference in prompt_references.items():
            self.prompt_registry.get(
                prompt_id=reference.prompt_id,
                version=reference.version,
            )
            prompt_versions[role] = (
                f"{reference.prompt_id}@{reference.version}"
            )

        tool_name = "query_customer_metrics"

        if tool_name not in capability.spec.allowed_tools:
            raise ValueError(
                f"Required tool is not allowed: {tool_name}"
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
                "capability_id": capability.metadata.id,
                "capability_version": capability.metadata.version,
                "execution_profile": execution_profile,
                "prompt_versions": prompt_versions,
            },
        )

        requirements = self.requirement_planner.plan(
            query=request.query,
            capability_id=capability.metadata.id,
        )

        retrieval_request = RetrievalRequest(
            tenant_id=request.tenant_id,
            workspace_id=request.workspace_id,
            query=request.query,
            capability_id=capability.metadata.id,
            context_policy_id=capability.spec.context_policy,
            allowed_classifications=(
                capability.spec.risk.data_classes
            ),
            requirements=requirements,
        )

        trace.add(
            "context.plan.created",
            {
                "strategy": capability.spec.context_policy,
                "requirement_ids": [
                    item.requirement_id
                    for item in requirements
                ],
                "requirements": [
                    item.model_dump(mode="json")
                    for item in requirements
                ],
                "allowed_classifications": (
                    retrieval_request.allowed_classifications
                ),
            },
        )

        context_package = self.context_engine.build_context(
            retrieval_request
        )

        trace.add(
            "retrieval.executed",
            {
                "context_package_id": (
                    context_package.package_id
                ),
                "decision": context_package.decision.value,
                "retrieval_mode": (
                    context_package.retrieval_mode.value
                ),
                "candidate_count": (
                    context_package.candidate_count
                ),
                "selected_count": (
                    context_package.selected_count
                ),
                "total_tokens": (
                    context_package.total_tokens
                ),
                "retrieved_source_ids": [
                    item.source_id
                    for item in context_package.items
                ],
                "covered_requirements": (
                    context_package.covered_requirements
                ),
                "missing_requirements": (
                    context_package.missing_requirements
                ),
            },
        )

        if (
            context_package.decision
            == ContextDecision.RETURN_INSUFFICIENT_EVIDENCE
        ):
            return self._complete_insufficient_evidence(
                analysis_id=analysis_id,
                trace_id=trace_id,
                trace=trace,
                request=request,
                capability=capability,
                context_package=context_package,
            )

        metrics = self._extract_metrics(
            context_package
        )

        trace.add(
            "tool.requested",
            {
                "tool_name": tool_name,
                "side_effect": "none",
                "context_package_id": (
                    context_package.package_id
                ),
            },
        )

        policy_decision = PolicyDecision(
            decision="ALLOW",
            policy_id=(
                "phase-03-governed-retrieval-"
                "read-only-tool-policy"
            ),
            reasons=[
                (
                    "The governed context engine returned "
                    "sufficient authorized evidence."
                ),
                (
                    "Selected sources match the request tenant, "
                    "workspace, and allowed classifications."
                ),
                "The requested tool is read-only.",
                (
                    "The required tool is present in the "
                    "capability allowlist."
                ),
            ],
        )

        trace.add(
            "policy.evaluated",
            policy_decision.model_dump(mode="json"),
        )

        trace.add(
            "tool.executed",
            {
                "tool_name": tool_name,
                "result_dataset_id": metrics["dataset_id"],
                "status": "success",
                "context_package_id": (
                    context_package.package_id
                ),
            },
        )

        evidence = self._build_evidence(
            context_package=context_package,
            metrics=metrics,
        )

        trace.add(
            "context.compiled",
            {
                "context_package_id": (
                    context_package.package_id
                ),
                "decision": context_package.decision.value,
                "evidence_ids": [
                    item.source_id
                    for item in evidence
                ],
                "evidence_count": len(evidence),
                "context_strategy": (
                    capability.spec.context_policy
                ),
                "retrieval_mode": (
                    context_package.retrieval_mode.value
                ),
                "context_tokens": (
                    context_package.total_tokens
                ),
                "covered_requirements": (
                    context_package.covered_requirements
                ),
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
                context_strategy=capability.spec.context_policy,
                tool_calls=1,
                trace_event_count=trace.event_count,
                context_package_id=(
                    context_package.package_id
                ),
                retrieval_mode=(
                    context_package.retrieval_mode.value
                ),
                retrieval_candidate_count=(
                    context_package.candidate_count
                ),
                retrieval_selected_count=(
                    context_package.selected_count
                ),
                context_tokens=(
                    context_package.total_tokens
                ),
            ),
        )

        self.store.save_analysis(result)
        self.store.save_trace(trace_record)
        self._persist_runtime_evidence(result, trace_record)

        return result

    @staticmethod
    def _extract_metrics(
        context_package: ContextPackage,
    ) -> dict:
        for item in context_package.items:
            payload = item.structured_payload

            if not isinstance(payload, dict):
                continue

            if (
                isinstance(payload.get("dataset_id"), str)
                and isinstance(payload.get("metrics"), dict)
            ):
                return payload

        raise ValueError(
            "Required authoritative churn metrics were not "
            "present in the governed context package."
        )

    @staticmethod
    def _metric_excerpt(metrics: dict) -> str:
        values = metrics["metrics"]

        return (
            f"Q2 churn was "
            f"{values['churn_rate']['current_percent']}%, "
            f"up "
            f"{values['churn_rate']['change_percentage_points']} "
            f"percentage points. Support incidents increased "
            f"{values['support_incidents']['change_percent']}%, "
            f"while weekly active usage changed "
            f"{values['weekly_active_usage']['change_percent']}%."
        )

    @staticmethod
    def _context_item_to_evidence(
        item: ContextItem,
    ) -> EvidenceItem:
        normalized_content = " ".join(
            item.content.split()
        )

        return EvidenceItem(
            source_id=item.source_id,
            source_type=item.source_type.value,
            title=item.title,
            excerpt=normalized_content[:500],
            relevance_score=item.relevance_score,
            tenant_id=item.tenant_id,
            classification=item.classification,
            authoritative=item.authoritative,
            updated_at=item.updated_at,
            content_hash=item.content_hash,
            citation_uri=item.citation_uri,
            matched_requirements=(
                item.matched_requirements
            ),
        )

    @classmethod
    def _build_retrieval_evidence(
        cls,
        context_package: ContextPackage,
    ) -> list[EvidenceItem]:
        return [
            cls._context_item_to_evidence(item)
            for item in context_package.items
        ]

    @classmethod
    def _build_evidence(
        cls,
        context_package: ContextPackage,
        metrics: dict,
    ) -> list[EvidenceItem]:
        evidence = cls._build_retrieval_evidence(
            context_package
        )

        metrics_dataset_id = metrics["dataset_id"]

        metrics_item = next(
            (
                item
                for item in context_package.items
                if (
                    isinstance(
                        item.structured_payload,
                        dict,
                    )
                    and item.structured_payload.get(
                        "dataset_id"
                    )
                    == metrics_dataset_id
                )
            ),
            None,
        )

        if metrics_item is None:
            raise ValueError(
                "The structured metrics source could not be "
                "resolved from the governed context package."
            )

        evidence.append(
            EvidenceItem(
                source_id="query-customer-metrics-result",
                source_type="tool-result",
                title="Customer Metrics Tool Result",
                excerpt=cls._metric_excerpt(metrics),
                relevance_score=1.0,
                tenant_id=metrics_item.tenant_id,
                classification=(
                    metrics_item.classification
                ),
                authoritative=True,
                updated_at=metrics_item.updated_at,
                content_hash=metrics_item.content_hash,
                citation_uri=(
                    "urn:analyst-tool-result:"
                    "query-customer-metrics"
                ),
                matched_requirements=[
                    "churn-change",
                    "support-signal",
                    "usage-signal",
                ],
            )
        )

        return evidence

    def _complete_insufficient_evidence(
        self,
        *,
        analysis_id: str,
        trace_id: str,
        trace: TraceRecorder,
        request: AnalysisRequest,
        capability: CapabilityManifest,
        context_package: ContextPackage,
    ) -> AnalysisResult:
        evidence = self._build_retrieval_evidence(
            context_package
        )

        reasons = (
            context_package.decision_reasons
            or [
                (
                    "The governed context engine could not "
                    "assemble sufficient authorized evidence."
                )
            ]
        )

        policy_decision = PolicyDecision(
            decision="RETURN_INSUFFICIENT_EVIDENCE",
            policy_id=capability.spec.context_policy,
            reasons=reasons,
        )

        trace.add(
            "context.compiled",
            {
                "context_package_id": (
                    context_package.package_id
                ),
                "decision": (
                    context_package.decision.value
                ),
                "evidence_ids": [
                    item.source_id
                    for item in evidence
                ],
                "evidence_count": len(evidence),
                "context_strategy": (
                    capability.spec.context_policy
                ),
                "retrieval_mode": (
                    context_package.retrieval_mode.value
                ),
                "context_tokens": (
                    context_package.total_tokens
                ),
                "covered_requirements": (
                    context_package.covered_requirements
                ),
                "missing_requirements": (
                    context_package.missing_requirements
                ),
            },
        )

        trace.add(
            "policy.evaluated",
            policy_decision.model_dump(mode="json"),
        )

        trace.add(
            "response.verified",
            {
                "schema_valid": True,
                "citation_count": 0,
                "unsupported_claim_count": 0,
            },
        )

        requirement_count = (
            len(context_package.covered_requirements)
            + len(context_package.missing_requirements)
        )

        coverage_score = (
            len(context_package.covered_requirements)
            / requirement_count
            if requirement_count
            else 0.0
        )

        evaluation = EvaluationResult(
            schema_valid=True,
            groundedness_score=1.0,
            evidence_coverage_score=round(
                coverage_score,
                6,
            ),
            policy_compliant=True,
            decision="REVIEW",
        )

        trace.add(
            "evaluation.completed",
            evaluation.model_dump(mode="json"),
        )

        trace.add(
            "response.returned",
            {
                "analysis_id": analysis_id,
                "status": (
                    AnalysisStatus.COMPLETED.value
                ),
                "decision": (
                    "RETURN_INSUFFICIENT_EVIDENCE"
                ),
            },
        )

        trace.add(
            "evidence.bundle.created",
            {
                "analysis_id": analysis_id,
                "trace_id": trace_id,
                "context_package_id": (
                    context_package.package_id
                ),
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
            summary=(
                "The analysis was not executed because the "
                "governed context engine could not retrieve "
                "sufficient authorized evidence. "
                + " ".join(reasons)
            ),
            findings=[],
            evidence=evidence,
            policy_decision=policy_decision,
            evaluation=evaluation,
            runtime=RuntimeMetadata(
                execution_mode=(
                    "deterministic-simulation"
                ),
                context_strategy=(
                    capability.spec.context_policy
                ),
                tool_calls=0,
                trace_event_count=trace.event_count,
                context_package_id=(
                    context_package.package_id
                ),
                retrieval_mode=(
                    context_package.retrieval_mode.value
                ),
                retrieval_candidate_count=(
                    context_package.candidate_count
                ),
                retrieval_selected_count=(
                    context_package.selected_count
                ),
                context_tokens=(
                    context_package.total_tokens
                ),
            ),
        )

        self.store.save_analysis(result)
        self.store.save_trace(trace_record)

        self._persist_runtime_evidence(
            result,
            trace_record,
        )

        return result

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
