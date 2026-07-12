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
        value.strip()
        for value in (result.stdout, result.stderr)
        if value.strip()
    )

    if result.returncode != 0:
        print(output)
        raise SystemExit(result.returncode)

    return output


def verify_runtime() -> dict:
    from fastapi.testclient import TestClient

    from apps.api.app.main import app

    payload = {
        "tenant_id": "tenant-demo",
        "workspace_id": "workspace-customer-intelligence",
        "user_id": "analyst-001",
        "capability_id": "customer-churn-analysis",
        "query": (
            "Explain why customer churn increased during Q2. "
            "Compare support incidents and product usage."
        ),
    }

    blocked_payload = {
        **payload,
        "tenant_id": "tenant-other",
    }

    with TestClient(app) as client:
        policies = client.get(
            "/api/v1/context-policies"
        )
        sources = client.get(
            "/api/v1/sources"
        )
        authorized = client.post(
            "/api/v1/analyses",
            json=payload,
        )
        blocked = client.post(
            "/api/v1/analyses",
            json=blocked_payload,
        )

        assert policies.status_code == 200
        assert sources.status_code == 200
        assert authorized.status_code == 201
        assert blocked.status_code == 201

        policy_items = policies.json()
        source_items = sources.json()
        authorized_result = authorized.json()
        blocked_result = blocked.json()

        assert len(policy_items) == 3
        assert len(source_items) == 2

        assert all(
            "path" not in item
            for item in source_items
        )

        assert (
            authorized_result["policy_decision"]["decision"]
            == "ALLOW"
        )
        assert (
            authorized_result["runtime"][
                "retrieval_selected_count"
            ]
            == 2
        )
        assert (
            authorized_result["runtime"]["tool_calls"]
            == 1
        )

        assert (
            blocked_result["policy_decision"]["decision"]
            == "RETURN_INSUFFICIENT_EVIDENCE"
        )
        assert (
            blocked_result["runtime"][
                "retrieval_selected_count"
            ]
            == 0
        )
        assert blocked_result["runtime"]["tool_calls"] == 0

        trace = client.get(
            f"/api/v1/traces/{blocked_result['trace_id']}"
        )

        assert trace.status_code == 200

        event_types = {
            event["event_type"]
            for event in trace.json()["events"]
        }

        assert "retrieval.executed" in event_types
        assert "tool.requested" not in event_types
        assert "tool.executed" not in event_types
        assert "model.simulated" not in event_types

    return {
        "application_version": app.version,
        "context_policy_count": len(policy_items),
        "source_count": len(source_items),
        "source_paths_exposed": False,
        "authorized_request": authorized_result,
        "cross_tenant_request": blocked_result,
        "cross_tenant_trace_events": sorted(event_types),
    }


def write_evidence(
    test_output: str,
    runtime_result: dict,
) -> tuple[Path, Path]:
    generated_at = datetime.now(
        timezone.utc
    ).isoformat()

    json_path = (
        ROOT
        / "evidence/benchmark-results/"
        "phase-03-retrieval-context-verification.json"
    )

    markdown_path = (
        ROOT
        / "evidence/"
        "PHASE_3_RETRIEVAL_CONTEXT_ENGINE_EVIDENCE.md"
    )

    json_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = {
        "phase": "Phase 3",
        "verification": "PASS",
        "generated_at": generated_at,
        "test_output": test_output,
        "runtime_verification": runtime_result,
    }

    json_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    authorized = runtime_result["authorized_request"]
    blocked = runtime_result["cross_tenant_request"]

    lines = [
        "# Phase 3 Retrieval and Context Engine Evidence",
        "",
        "## Verification Status",
        "",
        "**Result:** PASS",
        "",
        f"**Generated:** {generated_at}",
        "",
        "## Verified Outcomes",
        "",
        (
            "- Context policies registered: "
            f"`{runtime_result['context_policy_count']}`"
        ),
        (
            "- Governed sources registered: "
            f"`{runtime_result['source_count']}`"
        ),
        "- Source filesystem paths exposed: `NO`",
        (
            "- Authorized retrieval decision: "
            f"`{authorized['policy_decision']['decision']}`"
        ),
        (
            "- Authorized sources selected: "
            f"`{authorized['runtime']['retrieval_selected_count']}`"
        ),
        (
            "- Authorized tool calls: "
            f"`{authorized['runtime']['tool_calls']}`"
        ),
        (
            "- Cross-tenant decision: "
            f"`{blocked['policy_decision']['decision']}`"
        ),
        (
            "- Cross-tenant sources selected: "
            f"`{blocked['runtime']['retrieval_selected_count']}`"
        ),
        (
            "- Cross-tenant tool calls: "
            f"`{blocked['runtime']['tool_calls']}`"
        ),
        "- External model called: `NO`",
        "",
        "## Automated Test Result",
        "",
        "```text",
        test_output,
        "```",
        "",
        "## Authority Boundary",
        "",
        (
            "Phase 3 uses deterministic retrieval against "
            "synthetic local evidence."
        ),
        "",
        (
            "It has no production runtime authority, accesses no "
            "production data, and prevents tool and model execution "
            "when sufficient authorized evidence cannot be assembled."
        ),
        "",
    ]

    markdown_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    return json_path, markdown_path


def main() -> None:
    test_output = run_tests()
    runtime_result = verify_runtime()

    json_path, markdown_path = write_evidence(
        test_output=test_output,
        runtime_result=runtime_result,
    )

    print(test_output)
    print()
    print("[PASS] Phase 3 verification completed")
    print(f"[PASS] JSON evidence: {json_path}")
    print(f"[PASS] Markdown evidence: {markdown_path}")


if __name__ == "__main__":
    main()
