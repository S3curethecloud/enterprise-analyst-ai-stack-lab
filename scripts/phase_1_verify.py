from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))


def run_tests() -> str:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    output = "\n".join(
        value.strip()
        for value in [result.stdout, result.stderr]
        if value.strip()
    )

    if result.returncode != 0:
        print(output)
        raise SystemExit(result.returncode)

    return output


def verify_api() -> dict:
    from fastapi.testclient import TestClient

    from apps.api.app.main import app

    payload = {
        "tenant_id": "tenant-demo",
        "workspace_id": "workspace-customer-intelligence",
        "user_id": "analyst-001",
        "capability_id": "customer-churn-analysis",
        "query": (
            "Explain why customer churn increased during Q2. Compare support "
            "incidents and product usage, then provide an evidence-backed summary."
        ),
    }

    with TestClient(app) as client:
        health_response = client.get("/health")
        assert health_response.status_code == 200

        create_response = client.post(
            "/api/v1/analyses",
            json=payload,
        )
        assert create_response.status_code == 201

        analysis = create_response.json()

        read_response = client.get(
            f"/api/v1/analyses/{analysis['analysis_id']}"
        )
        assert read_response.status_code == 200

        trace_response = client.get(
            f"/api/v1/traces/{analysis['trace_id']}"
        )
        assert trace_response.status_code == 200

        trace = trace_response.json()

    assert analysis["status"] == "COMPLETED"
    assert analysis["evaluation"]["decision"] == "PASS"
    assert analysis["policy_decision"]["decision"] == "ALLOW"
    assert analysis["runtime"]["execution_mode"] == "deterministic-simulation"
    assert len(trace["events"]) == analysis["runtime"]["trace_event_count"]

    return {
        "health": health_response.json(),
        "analysis": analysis,
        "trace": trace,
    }


def write_evidence(test_output: str, verification: dict) -> None:
    evidence_directory = (
        REPOSITORY_ROOT / "evidence/benchmark-results"
    )
    evidence_directory.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(timezone.utc).isoformat()

    json_report = {
        "phase": "Phase 1",
        "verification": "PASS",
        "generated_at": generated_at,
        "test_output": test_output,
        "api_verification": verification,
    }

    json_path = evidence_directory / "phase-01-verification.json"
    json_path.write_text(
        json.dumps(json_report, indent=2),
        encoding="utf-8",
    )

    analysis = verification["analysis"]
    trace = verification["trace"]

    markdown_report = f"""# Phase 1 Deterministic Runtime Evidence

## Verification Status

**Result:** PASS

**Generated:** {generated_at}

## Implemented Controls

- FastAPI service foundation
- Typed Pydantic request and response contracts
- Deterministic analyst runtime
- Synthetic structured and unstructured evidence
- Read-only tool simulation
- Explicit policy decision
- Schema validation
- Grounded findings with evidence identifiers
- Runtime evaluation
- End-to-end trace capture
- Evidence bundle generation
- Analysis and trace retrieval endpoints
- Automated unit and integration tests

## Automated Test Result

```text
{test_output}
Verified Runtime Result
Analysis ID: {analysis["analysis_id"]}
Trace ID: {analysis["trace_id"]}
Status: {analysis["status"]}
Capability: {analysis["capability_id"]}
Policy decision: {analysis["policy_decision"]["decision"]}
Evaluation decision: {analysis["evaluation"]["decision"]}
Execution mode: {analysis["runtime"]["execution_mode"]}
Tool calls: {analysis["runtime"]["tool_calls"]}
Trace events: {len(trace["events"])}
Findings: {len(analysis["findings"])}
Evidence items: {len(analysis["evidence"])}
Authority Boundary

This phase uses deterministic simulation and synthetic data only.

No external model was called. No production data was accessed. No write-capable
enterprise tool was invoked. No production runtime authority exists.
"""

markdown_path = (
    REPOSITORY_ROOT
    / "evidence/PHASE_1_DETERMINISTIC_RUNTIME_EVIDENCE.md"
)
markdown_path.write_text(
    markdown_report,
    encoding="utf-8",
)

print(test_output)
print()
print("[PASS] Phase 1 API verification completed.")
print(f"[PASS] JSON evidence: {json_path}")
print(f"[PASS] Markdown evidence: {markdown_path}")

def main() -> None:
test_output = run_tests()
verification = verify_api()
write_evidence(test_output, verification)

if name == "main":
main()
