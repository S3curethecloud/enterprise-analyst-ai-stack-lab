from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from apps.api.app.context_contracts import (
    ContextPolicy,
    SourceCatalogDocument,
    SourceMetadata,
)


class ContextRegistryError(RuntimeError):
    """Raised when context configuration is invalid."""


class ContextPolicyNotFoundError(ContextRegistryError):
    """Raised when a context policy cannot be resolved."""


class SourceNotFoundError(ContextRegistryError):
    """Raised when a source cannot be resolved."""


class ContextPolicyRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._items: dict[str, ContextPolicy] = {}

    def load(self) -> ContextPolicyRegistry:
        items: dict[str, ContextPolicy] = {}

        for path in sorted(self.root.glob("*.yaml")):
            try:
                payload = yaml.safe_load(
                    path.read_text(encoding="utf-8")
                )
                policy = ContextPolicy.model_validate(payload)
            except (
                OSError,
                yaml.YAMLError,
                ValidationError,
            ) as exc:
                raise ContextRegistryError(
                    f"Invalid context policy {path}: {exc}"
                ) from exc

            if policy.policy_id in items:
                raise ContextRegistryError(
                    "Duplicate context policy ID: "
                    f"{policy.policy_id}"
                )

            items[policy.policy_id] = policy

        if not items:
            raise ContextRegistryError(
                f"No context policies found under {self.root}"
            )

        self._items = items
        return self

    def list_all(self) -> list[ContextPolicy]:
        return sorted(
            self._items.values(),
            key=lambda item: item.policy_id,
        )

    def get(self, policy_id: str) -> ContextPolicy:
        try:
            return self._items[policy_id]
        except KeyError as exc:
            raise ContextPolicyNotFoundError(
                f"Context policy not found: {policy_id}"
            ) from exc


class SourceCatalog:
    def __init__(
        self,
        catalog_path: Path,
        repository_root: Path,
    ) -> None:
        self.catalog_path = catalog_path
        self.repository_root = repository_root
        self._items: dict[str, SourceMetadata] = {}

    def load(self) -> SourceCatalog:
        try:
            payload = yaml.safe_load(
                self.catalog_path.read_text(
                    encoding="utf-8"
                )
            )
            catalog = SourceCatalogDocument.model_validate(
                payload
            )
        except (
            OSError,
            yaml.YAMLError,
            ValidationError,
        ) as exc:
            raise ContextRegistryError(
                f"Invalid source catalog "
                f"{self.catalog_path}: {exc}"
            ) from exc

        items: dict[str, SourceMetadata] = {}

        for source in catalog.sources:
            if source.source_id in items:
                raise ContextRegistryError(
                    f"Duplicate source ID: {source.source_id}"
                )

            source_path = self.repository_root / source.path

            if not source_path.is_file():
                raise ContextRegistryError(
                    f"Source path does not exist: {source_path}"
                )

            items[source.source_id] = source

        self._items = items
        return self

    def list_all(self) -> list[SourceMetadata]:
        return sorted(
            self._items.values(),
            key=lambda item: item.source_id,
        )

    def get(self, source_id: str) -> SourceMetadata:
        try:
            return self._items[source_id]
        except KeyError as exc:
            raise SourceNotFoundError(
                f"Source not found: {source_id}"
            ) from exc
