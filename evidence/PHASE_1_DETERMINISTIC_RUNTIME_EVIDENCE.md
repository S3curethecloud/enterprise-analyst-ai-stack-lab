# Phase 1 Deterministic Runtime Evidence

## Verification Status

**Result:** PASS

**Generated:** 2026-07-12T18:52:57.169627+00:00

## Automated Test Result

    ......                                                                   [100%]
    =============================== warnings summary ===============================
    .venv/lib/python3.12/site-packages/fastapi/testclient.py:1
      /home/cloudlab/enterprise-analyst-ai-stack-lab/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
        from starlette.testclient import TestClient as TestClient  # noqa
    
    tests/integration/test_api.py::test_unsupported_capability_returns_422
      /home/cloudlab/enterprise-analyst-ai-stack-lab/.venv/lib/python3.12/site-packages/fastapi/routing.py:344: StarletteDeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
        return await dependant.call(**values)
    
    -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

## Verified Runtime Result

- Analysis ID: `ana_8d16b3a51e3940c6`
- Trace ID: `trc_4d6f0a9d06134898`
- Status: `COMPLETED`
- Capability: `customer-churn-analysis`
- Policy decision: `ALLOW`
- Evaluation decision: `PASS`
- Execution mode: `deterministic-simulation`
- Tool calls: `1`
- Trace events: `14`
- Findings: `4`
- Evidence items: `3`

## Authority Boundary

This phase uses deterministic simulation and synthetic data only.

No external model was called. No production data was accessed. No write-capable enterprise tool was invoked.
