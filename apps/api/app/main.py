from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, status

from apps.api.app.contracts import (
    AnalysisRequest,
    AnalysisResult,
    HealthResponse,
    TraceRecord,
)
from apps.api.app.registry import (
    CapabilityRegistry,
    PromptRegistry,
    validate_registry_bindings,
)
from apps.api.app.registry_api import build_registry_router
from apps.api.app.runtime import DeterministicAnalystRuntime
from apps.api.app.store import AnalysisStore


APP_VERSION = "0.2.0"

app = FastAPI(
    title="Enterprise Analyst AI Stack API",
    version=APP_VERSION,
    description=(
        "Governed deterministic runtime foundation for the Enterprise Analyst AI Stack Lab."
    ),
)

repository_root = Path(__file__).resolve().parents[3]

capability_registry = CapabilityRegistry(
    repository_root / "capabilities"
).load()

prompt_registry = PromptRegistry(
    repository_root / "prompts"
).load()

validate_registry_bindings(
    capability_registry,
    prompt_registry,
)

store = AnalysisStore()

runtime = DeterministicAnalystRuntime(
    store=store,
    repository_root=repository_root,
    capability_registry=capability_registry,
    prompt_registry=prompt_registry,
)

app.include_router(
    build_registry_router(
        capability_registry=capability_registry,
        prompt_registry=prompt_registry,
    )
)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "project": "Enterprise Analyst AI Stack Lab",
        "service": "analyst-runtime-api",
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="analyst-runtime-api",
        version=APP_VERSION,
        execution_mode="deterministic-simulation",
    )


@app.post(
    "/api/v1/analyses",
    response_model=AnalysisResult,
    status_code=status.HTTP_201_CREATED,
)
async def create_analysis(request: AnalysisRequest) -> AnalysisResult:
    try:
        return await runtime.execute(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@app.get(
    "/api/v1/analyses/{analysis_id}",
    response_model=AnalysisResult,
)
async def get_analysis(analysis_id: str) -> AnalysisResult:
    analysis = store.get_analysis(analysis_id)

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found.",
        )

    return analysis


@app.get(
    "/api/v1/traces/{trace_id}",
    response_model=TraceRecord,
)
async def get_trace(trace_id: str) -> TraceRecord:
    trace = store.get_trace(trace_id)

    if trace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trace not found.",
        )

    return trace
