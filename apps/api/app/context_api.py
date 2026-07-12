from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from apps.api.app.context_contracts import (
    ContextPolicy,
    SourceMetadata,
    SourceMetadataView,
)
from apps.api.app.context_registry import (
    ContextPolicyNotFoundError,
    ContextPolicyRegistry,
    SourceCatalog,
    SourceNotFoundError,
)


def to_source_view(
    source: SourceMetadata,
) -> SourceMetadataView:
    return SourceMetadataView.model_validate(
        source.model_dump(
            exclude={"path"},
        )
    )


def build_context_router(
    policy_registry: ContextPolicyRegistry,
    source_catalog: SourceCatalog,
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1",
        tags=["context"],
    )

    @router.get(
        "/context-policies",
        response_model=list[ContextPolicy],
    )
    async def list_context_policies() -> list[ContextPolicy]:
        return policy_registry.list_all()

    @router.get(
        "/context-policies/{policy_id}",
        response_model=ContextPolicy,
    )
    async def get_context_policy(
        policy_id: str,
    ) -> ContextPolicy:
        try:
            return policy_registry.get(policy_id)
        except ContextPolicyNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

    @router.get(
        "/sources",
        response_model=list[SourceMetadataView],
    )
    async def list_sources() -> list[SourceMetadataView]:
        return [
            to_source_view(source)
            for source in source_catalog.list_all()
        ]

    @router.get(
        "/sources/{source_id}",
        response_model=SourceMetadataView,
    )
    async def get_source(
        source_id: str,
    ) -> SourceMetadataView:
        try:
            source = source_catalog.get(source_id)
        except SourceNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

        return to_source_view(source)

    return router
