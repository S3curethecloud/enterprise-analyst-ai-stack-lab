# Phase 3 Governed Retrieval and Context Engine Demo

## Objective

Demonstrate how the analyst runtime retrieves authorized evidence,
constructs a bounded context package, preserves provenance, and stops
execution when sufficient evidence is unavailable.

## Authorized Workflow

The analyst submits a customer-churn request for:

- Tenant: `tenant-demo`
- Workspace: `workspace-customer-intelligence`
- Capability: `customer-churn-analysis`

The runtime:

1. Resolves the active capability and context policy.
2. Plans information requirements.
3. Filters sources by tenant, workspace, classification, and lifecycle.
4. Ranks and deduplicates eligible evidence.
5. Applies the context token budget.
6. Builds a provenance-rich context package.
7. Executes the approved read-only tool.
8. Produces the deterministic analytical result and trace.

Expected controls:

- Retrieval decision: `ALLOW`
- Selected sources: `2`
- Tool calls: `1`
- Context policy: `churn-standard-v1`

## Cross-Tenant Workflow

The same request is submitted using an unauthorized tenant.

Expected controls:

- Retrieval decision: `RETURN_INSUFFICIENT_EVIDENCE`
- Selected sources: `0`
- Tool calls: `0`
- Model execution: `0`
- Findings: `0`

The runtime completes safely without leaking source content or invoking
downstream execution.

## Discovery APIs

- `GET /api/v1/context-policies`
- `GET /api/v1/context-policies/{policy_id}`
- `GET /api/v1/sources`
- `GET /api/v1/sources/{source_id}`

Discovery responses expose governed metadata only. Source content and
local filesystem paths are excluded.

## Verification

Run:

```bash
make verify
```

The Phase 3 gate must pass all automated tests and generate:

- `evidence/PHASE_3_RETRIEVAL_CONTEXT_ENGINE_EVIDENCE.md`
- `evidence/benchmark-results/phase-03-retrieval-context-verification.json`

## Authority Boundary

This phase uses synthetic local evidence only. It has no production
runtime authority, performs no production data access, and calls no
external model.
