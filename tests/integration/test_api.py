from fastapi.testclient import TestClient

from apps.api.app.main import app


client = TestClient(app)


def analysis_payload() -> dict:
    return {
        "tenant_id": "tenant-demo",
        "workspace_id": "workspace-customer-intelligence",
        "user_id": "analyst-001",
        "capability_id": "customer-churn-analysis",
        "query": (
            "Explain why customer churn increased during Q2. Compare support "
            "incidents and product usage, then provide an evidence-backed summary."
        ),
    }


def test_root_and_health_endpoints() -> None:
    root_response = client.get("/")
    health_response = client.get("/health")

    assert root_response.status_code == 200
    assert root_response.json()["service"] == "analyst-runtime-api"

    assert health_response.status_code == 200
    assert health_response.json()["status"] == "healthy"
    assert health_response.json()["execution_mode"] == "deterministic-simulation"


def test_create_and_retrieve_analysis_and_trace() -> None:
    create_response = client.post(
        "/api/v1/analyses",
        json=analysis_payload(),
    )

    assert create_response.status_code == 201

    created = create_response.json()

    assert created["status"] == "COMPLETED"
    assert created["evaluation"]["decision"] == "PASS"
    assert created["policy_decision"]["decision"] == "ALLOW"

    analysis_response = client.get(
        f"/api/v1/analyses/{created['analysis_id']}"
    )

    assert analysis_response.status_code == 200
    assert analysis_response.json()["analysis_id"] == created["analysis_id"]

    trace_response = client.get(
        f"/api/v1/traces/{created['trace_id']}"
    )

    assert trace_response.status_code == 200

    event_types = [
        event["event_type"]
        for event in trace_response.json()["events"]
    ]

    assert "request.received" in event_types
    assert "identity.resolved" in event_types
    assert "context.plan.created" in event_types
    assert "retrieval.executed" in event_types
    assert "context.compiled" in event_types
    assert "policy.evaluated" in event_types
    assert "tool.executed" in event_types
    assert "evaluation.completed" in event_types
    assert "evidence.bundle.created" in event_types

    capability_event = next(
        event
        for event in trace_response.json()["events"]
        if event["event_type"] == "capability.selected"
    )

    assert capability_event["details"]["capability_version"] == "1.0.0"
    assert capability_event["details"]["execution_profile"] == "churn-synthesis-v1"
    assert capability_event["details"]["prompt_versions"] == {
        "system": "analyst-core@v1",
        "task": "churn-analysis@v1",
        "verifier": "evidence-verifier@v1",
    }

    retrieval_event = next(
        event
        for event in trace_response.json()["events"]
        if event["event_type"] == "retrieval.executed"
    )

    assert retrieval_event["details"]["decision"] == "ALLOW"
    assert retrieval_event["details"]["retrieval_mode"] == (
        "standard"
    )
    assert retrieval_event["details"]["candidate_count"] == 2
    assert retrieval_event["details"]["selected_count"] == 2
    assert retrieval_event["details"]["total_tokens"] > 0
    assert (
        retrieval_event["details"]["missing_requirements"]
        == []
    )

    assert set(
        retrieval_event["details"]["retrieved_source_ids"]
    ) == {
        "customer-churn-snapshot-2026-q2",
        "q2-support-summary",
    }

    runtime = created["runtime"]

    assert runtime["context_package_id"].startswith("ctx_")
    assert runtime["retrieval_mode"] == "standard"
    assert runtime["retrieval_candidate_count"] == 2
    assert runtime["retrieval_selected_count"] == 2
    assert runtime["context_tokens"] > 0
    assert runtime["tool_calls"] == 1

    retrieved_evidence = [
        item
        for item in created["evidence"]
        if item["source_type"] != "tool-result"
    ]

    assert len(retrieved_evidence) == 2

    assert all(
        item["tenant_id"] == "tenant-demo"
        for item in retrieved_evidence
    )

    assert all(
        item["classification"] == "synthetic-internal"
        for item in retrieved_evidence
    )

    assert all(
        item["authoritative"] is True
        for item in retrieved_evidence
    )

    assert all(
        item["content_hash"]
        for item in retrieved_evidence
    )

    assert all(
        item["citation_uri"]
        for item in retrieved_evidence
    )


def test_unknown_resources_return_404() -> None:
    analysis_response = client.get("/api/v1/analyses/ana_missing")
    trace_response = client.get("/api/v1/traces/trc_missing")

    assert analysis_response.status_code == 404
    assert trace_response.status_code == 404


def test_unsupported_capability_returns_422() -> None:
    payload = analysis_payload()
    payload["capability_id"] = "unsupported-capability"

    response = client.post(
        "/api/v1/analyses",
        json=payload,
    )

    assert response.status_code == 422
    assert "Capability not found" in response.json()["detail"]


def test_registry_discovery_endpoints() -> None:
    capabilities_response = client.get("/api/v1/capabilities")
    prompts_response = client.get("/api/v1/prompts")

    assert capabilities_response.status_code == 200
    assert prompts_response.status_code == 200

    capabilities = capabilities_response.json()
    prompts = prompts_response.json()

    assert len(capabilities) == 3
    assert len(prompts) == 5

    capability_statuses = {
        item["metadata"]["id"]: item["metadata"]["status"]
        for item in capabilities
    }

    assert capability_statuses == {
        "customer-churn-analysis": "active",
        "executive-summary": "preview",
        "incident-trend-analysis": "preview",
    }

    prompt_keys = {
        f"{item['prompt_id']}@{item['version']}"
        for item in prompts
    }

    assert prompt_keys == {
        "analyst-core@v1",
        "churn-analysis@v1",
        "evidence-verifier@v1",
        "executive-summary@v1",
        "incident-trend-analysis@v1",
    }


def test_registry_detail_endpoints() -> None:
    capability_response = client.get(
        "/api/v1/capabilities/customer-churn-analysis"
    )

    prompt_response = client.get(
        "/api/v1/prompts/churn-analysis/versions/v1"
    )

    assert capability_response.status_code == 200
    assert prompt_response.status_code == 200

    capability = capability_response.json()
    prompt = prompt_response.json()

    assert capability["metadata"]["version"] == "1.0.0"
    assert capability["spec"]["runtime"]["execution_profile"] == (
        "churn-synthesis-v1"
    )

    assert prompt["prompt_id"] == "churn-analysis"
    assert prompt["role"] == "task"
    assert "content" not in prompt


def test_registry_missing_items_return_404() -> None:
    capability_response = client.get(
        "/api/v1/capabilities/missing-capability"
    )

    prompt_response = client.get(
        "/api/v1/prompts/missing-prompt/versions/v1"
    )

    assert capability_response.status_code == 404
    assert prompt_response.status_code == 404


def test_preview_capability_cannot_execute() -> None:
    payload = analysis_payload()
    payload["capability_id"] = "executive-summary"

    response = client.post(
        "/api/v1/analyses",
        json=payload,
    )

    assert response.status_code == 422
    assert "Capability is not active" in response.json()["detail"]


def test_cross_tenant_request_stops_before_tool_and_model_execution() -> None:
    payload = analysis_payload()
    payload["tenant_id"] = "tenant-other"

    response = client.post(
        "/api/v1/analyses",
        json=payload,
    )

    assert response.status_code == 201

    result = response.json()

    assert result["status"] == "COMPLETED"

    assert result["policy_decision"]["decision"] == (
        "RETURN_INSUFFICIENT_EVIDENCE"
    )

    assert result["policy_decision"]["policy_id"] == (
        "churn-standard-v1"
    )

    assert result["evaluation"]["decision"] == "REVIEW"
    assert result["evaluation"]["schema_valid"] is True
    assert result["evaluation"]["policy_compliant"] is True

    assert result["runtime"]["context_package_id"].startswith(
        "ctx_"
    )
    assert result["runtime"]["retrieval_mode"] == "standard"
    assert (
        result["runtime"]["retrieval_candidate_count"]
        == 0
    )
    assert (
        result["runtime"]["retrieval_selected_count"]
        == 0
    )
    assert result["runtime"]["context_tokens"] == 0
    assert result["runtime"]["tool_calls"] == 0

    assert result["findings"] == []
    assert result["evidence"] == []
    assert "not executed" in result["summary"]

    trace_response = client.get(
        f"/api/v1/traces/{result['trace_id']}"
    )

    assert trace_response.status_code == 200

    trace = trace_response.json()

    event_types = [
        event["event_type"]
        for event in trace["events"]
    ]

    assert "request.received" in event_types
    assert "identity.resolved" in event_types
    assert "context.plan.created" in event_types
    assert "retrieval.executed" in event_types
    assert "context.compiled" in event_types
    assert "policy.evaluated" in event_types
    assert "evaluation.completed" in event_types
    assert "evidence.bundle.created" in event_types

    assert "tool.requested" not in event_types
    assert "tool.executed" not in event_types
    assert "model.simulated" not in event_types

    retrieval_event = next(
        event
        for event in trace["events"]
        if event["event_type"] == "retrieval.executed"
    )

    assert retrieval_event["details"]["decision"] == (
        "RETURN_INSUFFICIENT_EVIDENCE"
    )
    assert retrieval_event["details"]["candidate_count"] == 0
    assert retrieval_event["details"]["selected_count"] == 0
    assert retrieval_event["details"]["total_tokens"] == 0

    assert set(
        retrieval_event["details"]["missing_requirements"]
    ) == {
        "churn-change",
        "support-signal",
        "usage-signal",
    }



def test_context_discovery_endpoints() -> None:
    policies = client.get("/api/v1/context-policies")
    sources = client.get("/api/v1/sources")

    assert policies.status_code == 200
    assert sources.status_code == 200

    assert {
        item["policy_id"]
        for item in policies.json()
    } == {
        "churn-fast-v1",
        "churn-standard-v1",
        "churn-deep-v1",
    }

    assert {
        item["source_id"]
        for item in sources.json()
    } == {
        "customer-churn-snapshot-2026-q2",
        "q2-support-summary",
    }

    assert all(
        "path" not in item
        for item in sources.json()
    )

    policy = client.get(
        "/api/v1/context-policies/churn-standard-v1"
    )
    source = client.get(
        "/api/v1/sources/"
        "customer-churn-snapshot-2026-q2"
    )

    assert policy.status_code == 200
    assert source.status_code == 200
    assert policy.json()["mode"] == "standard"
    assert source.json()["authoritative"] is True
    assert "path" not in source.json()

    assert client.get(
        "/api/v1/context-policies/missing-policy"
    ).status_code == 404

    assert client.get(
        "/api/v1/sources/missing-source"
    ).status_code == 404
