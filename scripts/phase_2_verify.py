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


def verify_registries() -> dict:
    from apps.api.app.registry import (
        CapabilityRegistry,
        PromptRegistry,
        validate_registry_bindings,
    )

    capabilities = CapabilityRegistry(
        ROOT / "capabilities"
    ).load()

    prompts = PromptRegistry(
        ROOT / "prompts"
    ).load()

    validate_registry_bindings(
        capabilities,
        prompts,
    )

    return {
        "capabilities": [
            {
                "id": item.metadata.id,
                "version": item.metadata.version,
                "status": item.metadata.status,
                "execution_profile": (
                    item.spec.runtime.execution_profile
                ),
                "prompt_versions": {
                    "system": (
                        f"{item.spec.prompt_bundle.system.prompt_id}"
                        f"@{item.spec.prompt_bundle.system.version}"
                    ),
                    "task": (
                        f"{item.spec.prompt_bundle.task.prompt_id}"
                        f"@{item.spec.prompt_bundle.task.version}"
                    ),
                    "verifier": (
                        f"{item.spec.prompt_bundle.verifier.prompt_id}"
                        f"@{item.spec.prompt_bundle.verifier.version}"
                    ),
                },
            }
            for item in capabilities.list_all()
        ],
        "prompts": [
            {
                "id": item.manifest.prompt_id,
                "version": item.manifest.version,
                "role": item.manifest.role,
                "status": item.manifest.status,
            }
            for item in prompts.list_all()
        ],
    }


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
        capabilities_response = client.get(
            "/api/v1/capabilities"
        )
        prompts_response = client.get(
            "/api/v1/prompts"
        )
        analysis_response = client.post(
            "/api/v1/analyses",
            json=payload,
        )

        assert capabilities_response.status_code == 200
        assert prompts_response.status_code == 200
        assert analysis_response.status_code == 201

        analysis = analysis_response.json()

        trace_response = client.get(
            f"/api/v1/traces/{analysis['trace_id']}"
        )

        assert trace_response.status_code == 200

        preview_payload = dict(payload)
        preview_payload["capability_id"] = "executive-summary"

        preview_response = client.post(
            "/api/v1/analyses",
            json=preview_payload,
        )

        assert preview_response.status_code == 422
        assert "Capability is not active" in (
            preview_response.json()["detail"]
        )

    trace = trace_response.json()

    capability_event = next(
        event
        for event in trace["events"]
        if event["event_type"] == "capability.selected"
    )

    assert capability_event["details"]["capability_version"] == "1.0.0"
    assert capability_event["details"]["prompt_versions"] == {
        "system": "analyst-core@v1",
        "task": "churn-analysis@v1",
        "verifier": "evidence-verifier@v1",
    }

    return {
        "capability_count": len(capabilities_response.json()),
        "prompt_count": len(prompts_response.json()),
        "analysis": analysis,
        "capability_trace_event": capability_event,
        "preview_capability_control": {
            "status_code": preview_response.status_code,
            "detail": preview_response.json()["detail"],
        },
    }


def write_evidence(
    test_output: str,
    registry_result: dict,
    api_result: dict,
) -> tuple[Path, Path]:
    generated_at = datetime.now(timezone.utc).isoformat()

    evidence_directory = ROOT / "evidence/benchmark-results"
    evidence_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path = (
        evidence_directory
        / "phase-02-capability-prompt-registry-verification.json"
    )

    markdown_path = (
        ROOT
        / "evidence/PHASE_2_CAPABILITY_PROMPT_REGISTRY_EVIDENCE.md"
    )

    report = {
        "phase": "Phase 2",
        "verification": "PASS",
        "generated_at": generated_at,
        "test_output": test_output,
        "registry_verification": registry_result,
        "api_verification": api_result,
    }

    json_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    analysis = api_result["analysis"]
    capability_event = api_result["capability_trace_event"]

    lines = [
        "# Phase 2 Capability and Prompt Registry Evidence",
        "",
        "## Verification Status",
        "",
        "**Result:** PASS",
        "",
        f"**Generated:** {generated_at}",
        "",
        "## Verified Outcomes",
        "",
        f"- Registered capabilities: `{api_result['capability_count']}`",
        f"- Registered prompt versions: `{api_result['prompt_count']}`",
        "- Capability-to-prompt bindings: `VALID`",
        "- Duplicate registry identifiers: `REJECTED`",
        "- Missing prompt content: `REJECTED`",
        "- Unknown capability execution: `REJECTED`",
        "- Preview capability execution: `REJECTED`",
        "- Prompt contents exposed through discovery API: `NO`",
        "",
        "## Executed Capability",
        "",
        f"- Capability: `{analysis['capability_id']}`",
        (
            "- Capability version: "
            f"`{capability_event['details']['capability_version']}`"
        ),
        (
            "- Execution profile: "
            f"`{capability_event['details']['execution_profile']}`"
        ),
        (
            "- Context policy: "
            f"`{analysis['runtime']['context_strategy']}`"
        ),
        (
            "- System prompt: "
            f"`{capability_event['details']['prompt_versions']['system']}`"
        ),
        (
            "- Task prompt: "
            f"`{capability_event['details']['prompt_versions']['task']}`"
        ),
        (
            "- Verifier prompt: "
            f"`{capability_event['details']['prompt_versions']['verifier']}`"
        ),
        "",
        "## Automated Test Result",
        "",
        "```text",
        test_output,
        "```",
        "",
        "## Authority Boundary",
        "",
        "Phase 2 provides registry-driven capability and prompt resolution.",
        "",
        "Only the customer-churn-analysis execution profile is active. "
        "The incident-trend-analysis and executive-summary capabilities "
        "remain preview-only and cannot execute.",
        "",
        "No external model was called and no production data was accessed.",
        "",
    ]

    markdown_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    return json_path, markdown_path


def main() -> None:
    test_output = run_tests()
    registry_result = verify_registries()
    api_result = verify_api()

    json_path, markdown_path = write_evidence(
        test_output=test_output,
        registry_result=registry_result,
        api_result=api_result,
    )

    print(test_output)
    print()
    print("[PASS] Phase 2 registry verification completed.")
    print(f"[PASS] JSON evidence: {json_path}")
    print(f"[PASS] Markdown evidence: {markdown_path}")


if __name__ == "__main__":
    main()
