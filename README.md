
Enterprise Analyst AI Stack Lab

A modular, governed, and observable AI platform for enterprise analytical workflows.

Purpose

This lab demonstrates how enterprise product teams can add new analyst capabilities without creating brittle prompt sprawl, duplicating tool integrations, weakening data boundaries, or bypassing evaluation and runtime governance.

The platform treats the following as versioned and testable components:

Analyst capabilities
Prompt bundles
Tool contracts
Metadata
Context policies
Memory policies
Output schemas
Evaluation suites
Runtime safety policies
Evidence bundles
Core Platform Outcome

A new analytical capability should be introduced through configuration and contracts rather than changes to the central runtime.

Each capability binds:

Supported task types
Prompt versions
Approved tools
Context strategy
Memory policy
Evaluation suite
Output schema
Runtime limits
Risk classification
Reference Workflow

The initial scenario analyzes customer churn using:

Customer-account metadata
Support incidents
Product-usage metrics
Approved enterprise documents

The platform produces an evidence-backed executive summary while enforcing tenant isolation, source authorization, tool policy, context budgets, output validation, and evaluation controls.

Architecture Domains
Analyst Experience Layer
AI Gateway
Capability Control Plane
Analyst Runtime
Context and Retrieval Plane
Governed Tool Gateway
Memory and State Plane
Trust, Evaluation and Evidence Plane

See ARCHITECTURE.md for the complete reference architecture.

Current Status

Phase: Phase 0 — Architecture Foundation

Data: Synthetic only

Runtime authority: None

Production authority: None

Repository Structure
apps/               User-facing APIs and interfaces
services/           Deployable platform services
packages/           Shared contracts and SDKs
capabilities/       Versioned analyst capability definitions
prompts/            Versioned prompt bundles
context-policies/   Retrieval and context-construction policies
memory-policies/    Memory lifecycle and authorization policies
policies/           Runtime policy definitions
tools/              Governed analyst tools
data/               Synthetic documents and structured fixtures
evals/              Datasets, graders, benchmarks, and reports
evidence/           Traces, decisions, reports, and screenshots
tests/              Unit, integration, security, regression, and isolation tests
docs/               Architecture decisions, diagrams, and operating guidance
Target Vertical Slice

The first executable milestone will:

Load a capability manifest.
Validate an analyst request.
Retrieve authorized context.
Invoke one typed read-only tool.
Produce a schema-valid result.
Evaluate the result.
Record policy and runtime decisions.
Generate an evidence bundle.
Governing Documents
SYSTEM-OF-TRUTH.md
ARCHITECTURE.md
DESIGN-PRINCIPLES.md
THREAT-MODEL.md
ROADMAP.md
License

This repository is intended for architecture education, engineering demonstration, and portfolio evidence. Production adoption requires organization-specific security, privacy, compliance, reliability, and operational review.

## Local Quick Start

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    make verify
    make run

API documentation:

    http://127.0.0.1:8000/docs

Run the HTTP smoke test from a second terminal:

    cd ~/enterprise-analyst-ai-stack-lab
    source .venv/bin/activate
    make smoke

## Phase 1 API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | / | Service metadata |
| GET | /health | Runtime health |
| POST | /api/v1/analyses | Execute deterministic analysis |
| GET | /api/v1/analyses/{analysis_id} | Retrieve an analysis |
| GET | /api/v1/traces/{trace_id} | Retrieve an execution trace |

## Phase 1 Execution Boundary

Phase 1 uses deterministic simulation and synthetic evidence.

It does not call an external model, access production data, invoke write-capable
tools, or possess production runtime authority.

## Phase 2 Capability Architecture

Phase 2 replaces hard-coded capability selection with validated,
versioned capability and prompt registries.

The repository currently contains:

- Three capability manifests
- Five versioned prompt artifacts
- Capability-to-prompt binding validation
- Capability lifecycle enforcement
- Registry discovery APIs
- Registry-driven runtime resolution
- Prompt-version trace evidence

Only `customer-churn-analysis` is active. The
`incident-trend-analysis` and `executive-summary` capabilities remain
preview-only until their execution profiles are implemented.

### Registry Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /api/v1/capabilities | List capability manifests |
| GET | /api/v1/capabilities/{capability_id} | Retrieve one capability |
| GET | /api/v1/prompts | List prompt metadata |
| GET | /api/v1/prompts/{prompt_id}/versions/{version} | Retrieve prompt metadata |

Prompt content is intentionally excluded from the discovery API.
