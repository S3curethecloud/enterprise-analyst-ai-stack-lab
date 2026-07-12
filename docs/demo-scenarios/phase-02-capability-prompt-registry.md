# Phase 2 Demo Scenario — Capability and Prompt Registries

## Purpose

Phase 2 replaces hard-coded capability selection with versioned,
validated capability and prompt registries.

## Registered Capabilities

### customer-churn-analysis

Status: active

Execution profile: churn-synthesis-v1

This capability can execute through the deterministic runtime.

### incident-trend-analysis

Status: preview

Execution profile: incident-trend-v1

The manifest and prompt bindings are valid, but the execution profile
has not yet been implemented.

### executive-summary

Status: preview

Execution profile: executive-summary-v1

The manifest and prompt bindings are valid, but the execution profile
has not yet been implemented.

## Registry Controls

The platform validates:

- Capability schema
- Capability identifiers and versions
- Prompt identifiers and versions
- Prompt roles
- Prompt content-file existence
- Duplicate capability identifiers
- Duplicate prompt versions
- Capability-to-prompt bindings
- Capability lifecycle status
- Tool allowlists
- Runtime budgets
- Context and memory policy references

## Runtime Behavior

An analysis request resolves its capability from the registry.

The runtime then resolves:

1. Capability version
2. Execution profile
3. System prompt version
4. Task prompt version
5. Verifier prompt version
6. Allowed tools
7. Context policy
8. Memory policy
9. Evaluation suite
10. Runtime limits

Preview and disabled capabilities cannot execute.

## Discovery Endpoints

- GET /api/v1/capabilities
- GET /api/v1/capabilities/{capability_id}
- GET /api/v1/prompts
- GET /api/v1/prompts/{prompt_id}/versions/{version}

Prompt discovery returns metadata only. Governed prompt content is not
returned through the public registry API.
