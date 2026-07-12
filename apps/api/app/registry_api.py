from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from apps.api.app.registry import (
    CapabilityManifest,
    CapabilityRegistry,
    PromptManifest,
    PromptRegistry,
    RegistryItemNotFoundError,
)


def build_registry_router(
    capability_registry: CapabilityRegistry,
    prompt_registry: PromptRegistry,
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1",
        tags=["registries"],
    )

    @router.get(
        "/capabilities",
        response_model=list[CapabilityManifest],
    )
    async def list_capabilities() -> list[CapabilityManifest]:
        return capability_registry.list_all()

    @router.get(
        "/capabilities/{capability_id}",
        response_model=CapabilityManifest,
    )
    async def get_capability(
        capability_id: str,
    ) -> CapabilityManifest:
        try:
            return capability_registry.get(capability_id)
        except RegistryItemNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

    @router.get(
        "/prompts",
        response_model=list[PromptManifest],
    )
    async def list_prompts() -> list[PromptManifest]:
        return [
            artifact.manifest
            for artifact in prompt_registry.list_all()
        ]

    @router.get(
        "/prompts/{prompt_id}/versions/{version}",
        response_model=PromptManifest,
    )
    async def get_prompt(
        prompt_id: str,
        version: str,
    ) -> PromptManifest:
        try:
            return prompt_registry.get(
                prompt_id=prompt_id,
                version=version,
            ).manifest
        except RegistryItemNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

    return router
