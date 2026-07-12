from __future__ import annotations

import json
import math
from hashlib import sha256
from pathlib import Path
from typing import Any

from apps.api.app.context_contracts import (
    SourceDocument,
    SourceMetadata,
    SourceType,
)


class SourceAdapterError(RuntimeError):
    """Raised when a governed source cannot be loaded."""


def estimate_tokens(content: str) -> int:
    return max(1, math.ceil(len(content) / 4))


def content_digest(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def flatten_structured_value(
    value: Any,
    path: str = "",
) -> list[str]:
    lines: list[str] = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            lines.extend(
                flatten_structured_value(
                    child,
                    child_path,
                )
            )
        return lines

    if isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}.{index}" if path else str(index)
            lines.extend(
                flatten_structured_value(
                    child,
                    child_path,
                )
            )
        return lines

    normalized_path = (
        path.replace("_", " ")
        .replace("-", " ")
        .replace(".", " ")
    )

    lines.append(
        f"{normalized_path}: {value}".strip()
    )

    return lines


class StructuredJsonAdapter:
    def load(
        self,
        metadata: SourceMetadata,
        repository_root: Path,
    ) -> SourceDocument:
        path = repository_root / metadata.path

        try:
            raw_content = path.read_text(encoding="utf-8")
            payload = json.loads(raw_content)
        except (OSError, json.JSONDecodeError) as exc:
            raise SourceAdapterError(
                f"Unable to load structured source "
                f"{metadata.source_id}: {exc}"
            ) from exc

        searchable_content = "\n".join(
            flatten_structured_value(payload)
        )

        return SourceDocument(
            metadata=metadata,
            content=searchable_content,
            structured_payload=payload,
            content_hash=content_digest(raw_content),
            estimated_tokens=estimate_tokens(
                searchable_content
            ),
        )


class MarkdownDocumentAdapter:
    def load(
        self,
        metadata: SourceMetadata,
        repository_root: Path,
    ) -> SourceDocument:
        path = repository_root / metadata.path

        try:
            content = path.read_text(
                encoding="utf-8"
            ).strip()
        except OSError as exc:
            raise SourceAdapterError(
                f"Unable to load document source "
                f"{metadata.source_id}: {exc}"
            ) from exc

        if not content:
            raise SourceAdapterError(
                f"Document source is empty: "
                f"{metadata.source_id}"
            )

        return SourceDocument(
            metadata=metadata,
            content=content,
            structured_payload=None,
            content_hash=content_digest(content),
            estimated_tokens=estimate_tokens(content),
        )


class SourceDocumentLoader:
    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root
        self.structured_adapter = StructuredJsonAdapter()
        self.document_adapter = MarkdownDocumentAdapter()

    def load(
        self,
        metadata: SourceMetadata,
    ) -> SourceDocument:
        if metadata.source_type == SourceType.STRUCTURED_DATA:
            return self.structured_adapter.load(
                metadata=metadata,
                repository_root=self.repository_root,
            )

        if metadata.source_type == SourceType.DOCUMENT:
            return self.document_adapter.load(
                metadata=metadata,
                repository_root=self.repository_root,
            )

        raise SourceAdapterError(
            "No source adapter is registered for "
            f"{metadata.source_type.value}"
        )
