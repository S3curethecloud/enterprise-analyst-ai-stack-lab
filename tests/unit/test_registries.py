from pathlib import Path

import pytest
import yaml

from apps.api.app.registry import (
    CapabilityRegistry,
    PromptRegistry,
    RegistryError,
    RegistryItemNotFoundError,
    validate_registry_bindings,
)


def write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def create_prompt(
    root: Path,
    prompt_id: str,
    version: str,
    role: str,
) -> None:
    prompt_directory = root / prompt_id
    prompt_directory.mkdir(parents=True, exist_ok=True)

    content_name = f"{version}.md"

    write_yaml(
        prompt_directory / f"{version}.yaml",
        {
            "api_version": "analyst.securethecloud.dev/v1",
            "kind": "PromptArtifact",
            "prompt_id": prompt_id,
            "version": version,
            "role": role,
            "owner": "platform-team",
            "description": f"Test prompt for {prompt_id}",
            "status": "active",
            "content_file": content_name,
        },
    )

    (prompt_directory / content_name).write_text(
        f"Prompt content for {prompt_id}.",
        encoding="utf-8",
    )


def create_capability(root: Path) -> None:
    write_yaml(
        root / "customer-churn-analysis" / "manifest.yaml",
        {
            "api_version": "analyst.securethecloud.dev/v1",
            "kind": "AnalystCapability",
            "metadata": {
                "id": "customer-churn-analysis",
                "version": "1.0.0",
                "owner": "customer-intelligence-team",
                "description": "Analyze customer churn.",
                "status": "active",
            },
            "spec": {
                "task_types": ["churn_analysis"],
                "prompt_bundle": {
                    "system": {
                        "prompt_id": "analyst-core",
                        "version": "v1",
                    },
                    "task": {
                        "prompt_id": "churn-analysis",
                        "version": "v1",
                    },
                    "verifier": {
                        "prompt_id": "evidence-verifier",
                        "version": "v1",
                    },
                },
                "allowed_tools": ["query_customer_metrics"],
                "context_policy": "churn-standard-v1",
                "memory_policy": "workspace-isolated-v1",
                "evaluation_suite": "churn-analysis-v1",
                "output_schema": "schemas/churn-analysis-v1.json",
                "runtime": {
                    "execution_profile": "churn-synthesis-v1",
                    "maximum_tool_calls": 4,
                    "maximum_context_tokens": 12000,
                    "timeout_seconds": 45,
                },
                "risk": {
                    "classification": "moderate",
                    "data_classes": ["synthetic-internal"],
                    "approval_required_for": [],
                },
            },
        },
    )


def test_registry_loads_and_validates_bindings(
    tmp_path: Path,
) -> None:
    capability_root = tmp_path / "capabilities"
    prompt_root = tmp_path / "prompts"

    create_prompt(prompt_root, "analyst-core", "v1", "system")
    create_prompt(prompt_root, "churn-analysis", "v1", "task")
    create_prompt(
        prompt_root,
        "evidence-verifier",
        "v1",
        "verifier",
    )
    create_capability(capability_root)

    capabilities = CapabilityRegistry(capability_root).load()
    prompts = PromptRegistry(prompt_root).load()

    validate_registry_bindings(capabilities, prompts)

    capability = capabilities.get("customer-churn-analysis")
    task_prompt = prompts.get("churn-analysis", "v1")

    assert capability.metadata.version == "1.0.0"
    assert capability.spec.runtime.maximum_tool_calls == 4
    assert task_prompt.manifest.role == "task"
    assert "Prompt content" in task_prompt.content


def test_unknown_capability_is_rejected(
    tmp_path: Path,
) -> None:
    capability_root = tmp_path / "capabilities"
    create_capability(capability_root)

    registry = CapabilityRegistry(capability_root).load()

    with pytest.raises(
        RegistryItemNotFoundError,
        match="Capability not found",
    ):
        registry.get("missing-capability")


def test_missing_prompt_content_is_rejected(
    tmp_path: Path,
) -> None:
    prompt_root = tmp_path / "prompts"

    write_yaml(
        prompt_root / "analyst-core" / "v1.yaml",
        {
            "api_version": "analyst.securethecloud.dev/v1",
            "kind": "PromptArtifact",
            "prompt_id": "analyst-core",
            "version": "v1",
            "role": "system",
            "owner": "platform-team",
            "description": "System prompt.",
            "status": "active",
            "content_file": "missing.md",
        },
    )

    with pytest.raises(
        RegistryError,
        match="does not exist",
    ):
        PromptRegistry(prompt_root).load()


def test_repository_registries_are_valid() -> None:
    repository_root = Path(__file__).resolve().parents[2]

    capabilities = CapabilityRegistry(
        repository_root / "capabilities"
    ).load()

    prompts = PromptRegistry(
        repository_root / "prompts"
    ).load()

    validate_registry_bindings(capabilities, prompts)

    assert len(capabilities.list_all()) == 3
    assert len(prompts.list_all()) == 5

    capability_ids = {
        item.metadata.id
        for item in capabilities.list_all()
    }

    assert capability_ids == {
        "customer-churn-analysis",
        "incident-trend-analysis",
        "executive-summary",
    }


def test_repository_capabilities_reference_versioned_prompts() -> None:
    repository_root = Path(__file__).resolve().parents[2]

    capabilities = CapabilityRegistry(
        repository_root / "capabilities"
    ).load()

    prompts = PromptRegistry(
        repository_root / "prompts"
    ).load()

    for capability in capabilities.list_all():
        bundle = capability.spec.prompt_bundle

        system_prompt = prompts.get(
            bundle.system.prompt_id,
            bundle.system.version,
        )
        task_prompt = prompts.get(
            bundle.task.prompt_id,
            bundle.task.version,
        )
        verifier_prompt = prompts.get(
            bundle.verifier.prompt_id,
            bundle.verifier.version,
        )

        assert system_prompt.manifest.role == "system"
        assert task_prompt.manifest.role == "task"
        assert verifier_prompt.manifest.role == "verifier"
