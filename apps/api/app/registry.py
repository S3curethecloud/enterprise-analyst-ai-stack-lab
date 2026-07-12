from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, ValidationError


class RegistryError(RuntimeError):
    """Base exception for registry loading and validation failures."""


class RegistryItemNotFoundError(RegistryError):
    """Raised when a requested registry item does not exist."""


class PromptReference(BaseModel):
    prompt_id: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=32)


class PromptBundle(BaseModel):
    system: PromptReference
    task: PromptReference
    verifier: PromptReference


class CapabilityMetadata(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=32)
    owner: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=1000)
    status: Literal["active", "preview", "disabled"]


class CapabilityRuntime(BaseModel):
    execution_profile: str = Field(min_length=1, max_length=128)
    maximum_tool_calls: int = Field(ge=0, le=100)
    maximum_context_tokens: int = Field(ge=256, le=1_000_000)
    timeout_seconds: int = Field(ge=1, le=3600)


class CapabilityRisk(BaseModel):
    classification: Literal["low", "moderate", "high", "critical"]
    data_classes: list[str] = Field(default_factory=list)
    approval_required_for: list[str] = Field(default_factory=list)


class CapabilitySpec(BaseModel):
    task_types: list[str] = Field(min_length=1)
    prompt_bundle: PromptBundle
    allowed_tools: list[str] = Field(default_factory=list)
    context_policy: str = Field(min_length=1, max_length=128)
    memory_policy: str = Field(min_length=1, max_length=128)
    evaluation_suite: str = Field(min_length=1, max_length=128)
    output_schema: str = Field(min_length=1, max_length=256)
    runtime: CapabilityRuntime
    risk: CapabilityRisk


class CapabilityManifest(BaseModel):
    api_version: Literal["analyst.securethecloud.dev/v1"]
    kind: Literal["AnalystCapability"]
    metadata: CapabilityMetadata
    spec: CapabilitySpec


class PromptManifest(BaseModel):
    api_version: Literal["analyst.securethecloud.dev/v1"]
    kind: Literal["PromptArtifact"]
    prompt_id: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=32)
    role: Literal["system", "task", "verifier"]
    owner: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=1000)
    status: Literal["active", "preview", "deprecated"]
    content_file: str = Field(min_length=1, max_length=256)


class PromptArtifact(BaseModel):
    manifest: PromptManifest
    content: str = Field(min_length=1)


class CapabilityRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._items: dict[str, CapabilityManifest] = {}

    def load(self) -> CapabilityRegistry:
        items: dict[str, CapabilityManifest] = {}

        for manifest_path in sorted(self.root.glob("*/manifest.yaml")):
            try:
                raw = yaml.safe_load(
                    manifest_path.read_text(encoding="utf-8")
                )
                manifest = CapabilityManifest.model_validate(raw)
            except (OSError, yaml.YAMLError, ValidationError) as exc:
                raise RegistryError(
                    f"Invalid capability manifest {manifest_path}: {exc}"
                ) from exc

            capability_id = manifest.metadata.id

            if capability_id in items:
                raise RegistryError(
                    f"Duplicate capability ID: {capability_id}"
                )

            items[capability_id] = manifest

        if not items:
            raise RegistryError(
                f"No capability manifests found under {self.root}"
            )

        self._items = items
        return self

    def list_all(self) -> list[CapabilityManifest]:
        return sorted(
            self._items.values(),
            key=lambda item: item.metadata.id,
        )

    def get(self, capability_id: str) -> CapabilityManifest:
        try:
            return self._items[capability_id]
        except KeyError as exc:
            raise RegistryItemNotFoundError(
                f"Capability not found: {capability_id}"
            ) from exc


class PromptRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._items: dict[str, PromptArtifact] = {}

    @staticmethod
    def key(prompt_id: str, version: str) -> str:
        return f"{prompt_id}@{version}"

    def load(self) -> PromptRegistry:
        items: dict[str, PromptArtifact] = {}

        for manifest_path in sorted(self.root.glob("*/v*.yaml")):
            try:
                raw = yaml.safe_load(
                    manifest_path.read_text(encoding="utf-8")
                )
                manifest = PromptManifest.model_validate(raw)
            except (OSError, yaml.YAMLError, ValidationError) as exc:
                raise RegistryError(
                    f"Invalid prompt manifest {manifest_path}: {exc}"
                ) from exc

            content_path = manifest_path.parent / manifest.content_file

            if not content_path.is_file():
                raise RegistryError(
                    f"Prompt content file does not exist: {content_path}"
                )

            content = content_path.read_text(encoding="utf-8").strip()

            artifact = PromptArtifact(
                manifest=manifest,
                content=content,
            )

            registry_key = self.key(
                manifest.prompt_id,
                manifest.version,
            )

            if registry_key in items:
                raise RegistryError(
                    f"Duplicate prompt version: {registry_key}"
                )

            items[registry_key] = artifact

        if not items:
            raise RegistryError(
                f"No prompt manifests found under {self.root}"
            )

        self._items = items
        return self

    def list_all(self) -> list[PromptArtifact]:
        return sorted(
            self._items.values(),
            key=lambda item: (
                item.manifest.prompt_id,
                item.manifest.version,
            ),
        )

    def get(
        self,
        prompt_id: str,
        version: str,
    ) -> PromptArtifact:
        registry_key = self.key(prompt_id, version)

        try:
            return self._items[registry_key]
        except KeyError as exc:
            raise RegistryItemNotFoundError(
                f"Prompt not found: {registry_key}"
            ) from exc


def validate_registry_bindings(
    capabilities: CapabilityRegistry,
    prompts: PromptRegistry,
) -> None:
    for capability in capabilities.list_all():
        bundle = capability.spec.prompt_bundle

        for reference in (
            bundle.system,
            bundle.task,
            bundle.verifier,
        ):
            prompts.get(
                prompt_id=reference.prompt_id,
                version=reference.version,
            )
