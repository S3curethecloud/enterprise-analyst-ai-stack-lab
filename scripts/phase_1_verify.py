from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run_tests() -> str:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    output = "\n".join(
        part.strip()
        for part in (result.stdout, result.stderr)
        if part.strip()
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
            "Explain why customer churn increased during Q2. "
            "Compare support incidents and product usage, then "
            "provide an evidence-backed executive summary."
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

        analysis_response = client.get(
            f"/api/v1/analyses/{analysis['analysis_id']}"
        )
        assert analysis_response.status_code == 200

        trace_response = client.get(
            f"/api/v1/traces/{analysis['trace_id']}"
        )
        assert trace_response.status_code == 200

        trace = trace_response.json()

    assert analysis["status"] == "COMPLETED"
    assert analysis["policy_decision"]["decision"] == "ALLOW"
    assert analysis["evaluation"]["decision"] == "PASS"
    assert analysis["evaluation"]["schema_valid"] is True
    assert analysis["runtime"]["execution_mode"] == "deterministic-simulation"
    assert len(trace["events"]) == analysis["runtime"]["trace_event_count"]

    return {
        "health": health_response.json(),
        "analysis": analysis,
        "trace": trace,
    }


def write_evidence(test_output: str, verification: dict) -> tuple[Path, Path]:
    generated_at = datetime.now(timezone.utc).isoformat()

    benchmark_directory = ROOT / "evidence/benchmark-results"
    benchmark_directory.mkdir(parents=True, exist_ok=True)

    json_path = benchmark_directory / "phase-01-verification.json"
    markdown_path = (
        ROOT / "evidence/PHASE_1_DETERMINISTIC_RUNTIME_EVIDENCE.md"
    )

    report = {
        "phase": "Phase 1",
        "verification": "PASS",
        "generated_at": generated_at,
        "test_output": test_output,
        "api_verification": verification,
    }

    json_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    analysis = verification["analysis"]
    trace = verification["trace"]

    markdown_lines = [
        "# Phase 1 Deterministic Runtime Evidence",
        "",
        "## Verification Status",
        "",
        "**Result:** PASS",
        "",
        f"**Generated:** {generated_at}",
        "",
        "## Automated Test Result",
        "",
        f"    {test_output.replace(chr(10), chr(10) + '    ')}",
        "",
        "## Verified Runtime Result",
        "",
        f"- Analysis ID: `{analysis['analysis_id']}`",
        f"- Trace ID: `{analysis['trace_id']}`",
        f"- Status: `{analysis['status']}`",
        f"- Capability: `{analysis['capability_id']}`",
        (
            "- Policy decision: "
            f"`{analysis['policy_decision']['decision']}`"
        ),
        (
            "- Evaluation decision: "
            f"`{analysis['evaluation']['decision']}`"
        ),
        (
            "- Execution mode: "
            f"`{analysis['runtime']['execution_mode']}`"
        ),
        f"- Tool calls: `{analysis['runtime']['tool_calls']}`",
        f"- Trace events: `{len(trace['events'])}`",
        f"- Findings: `{len(analysis['findings'])}`",
        f"- Evidence items: `{len(analysis['evidence'])}`",
        "",
        "## Authority Boundary",
        "",
        "This phase uses deterministic simulation and synthetic data only.",
        "",
        "No external model was called. No production data was accessed. "
        "No write-capable enterprise tool was invoked.",
        "",
    ]

    markdown_path.write_text(
        "\n".join(markdown_lines),
        encoding="utf-8",
    )

    return json_path, markdown_path


def main() -> None:
    test_output = run_tests()
    verification = verify_api()
    json_path, markdown_path = write_evidence(
        test_output=test_output,
        verification=verification,
    )

    print(test_output)
    print()
    print("[PASS] Phase 1 API verification completed.")
    print(f"[PASS] JSON evidence: {json_path}")
    print(f"[PASS] Markdown evidence: {markdown_path}")


if __name__ == "__main__":
    main()
