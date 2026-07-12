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

