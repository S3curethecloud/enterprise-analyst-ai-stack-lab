# Enterprise Analyst AI Stack Lab — System of Truth

## 1. Authority

This document is the authoritative source for the scope, design intent, operating boundaries, and implementation status of the Enterprise Analyst AI Stack Lab.

When implementation details, diagrams, README content, or individual service documentation conflict with this document, this document takes precedence until it is intentionally updated.

## 2. Project Identity

**Project:** Enterprise Analyst AI Stack Lab

**Repository:** `enterprise-analyst-ai-stack-lab`

**Purpose:** Build a modular, governed, and observable AI platform for enterprise analytical workflows.

The platform demonstrates how product teams can introduce new analyst capabilities through versioned contracts, prompt bundles, tools, context policies, memory policies, output schemas, and evaluation suites without modifying the core runtime.

## 3. Core Problem

Enterprise AI applications frequently become brittle because:

- Prompts are embedded directly in application code.
- Tool definitions are duplicated across products.
- Context construction is tightly coupled to one workflow.
- Memory has unclear scope, retention, and authorization boundaries.
- Model-provider APIs leak into product logic.
- Evaluation is performed manually or only after release.
- Runtime policy decisions are not captured as evidence.
- Product teams create independent agent implementations that cannot be governed consistently.

This lab addresses those problems through reusable platform abstractions.

## 4. Primary Outcome

The platform must allow a product team to add a new analytical capability using:

1. A capability manifest.
2. A versioned prompt bundle.
3. An approved tool allowlist.
4. A context policy.
5. A memory policy.
6. An output schema.
7. A risk profile.
8. An evaluation suite.

The product team must not need to modify the central runtime orchestration logic for a standard new capability.

## 5. Reference Use Case

The initial reference workflow is customer-churn analysis.

Example analyst request:

> Explain why customer churn increased during the second quarter. Compare support incidents, product usage, and account metadata, then produce an evidence-backed executive summary.

The platform must:

1. Authenticate and identify the requester.
2. Resolve tenant and workspace boundaries.
3. Classify the requested task.
4. Select an approved capability.
5. Build an information requirement plan.
6. Retrieve authorized structured and unstructured information.
7. Execute approved tools through typed interfaces.
8. Construct context within token, latency, and cost budgets.
9. Produce a schema-valid analytical response.
10. Attach evidence and provenance.
11. Evaluate response quality and safety.
12. Record an end-to-end decision trace.

## 6. Architectural Domains

The platform is divided into the following domains:

- Analyst Experience Layer
- AI Gateway
- Capability Control Plane
- Analyst Runtime
- Context Engine
- Retrieval Service
- Governed Tool Gateway
- Memory and State Plane
- Policy Engine
- Evaluation Service
- Evidence Service
- Observability Plane

## 7. Trust Boundaries

The system must preserve explicit boundaries between:

- Users and the AI gateway
- Product capabilities and the core runtime
- The model and enterprise tools
- The model and enterprise data
- Thread state and durable memory
- Tenant data and shared platform services
- Runtime execution and human approval
- Operational telemetry and sensitive business data

## 8. Runtime Decision Model

The policy layer may return:

- `ALLOW`
- `DENY`
- `REDACT`
- `REQUIRE_APPROVAL`
- `RETRY_WITH_RESTRICTED_CONTEXT`
- `RETURN_INSUFFICIENT_EVIDENCE`
- `ESCALATE_TO_HUMAN`

No tool invocation or durable memory write may bypass the policy decision path.

## 9. Design Principles

1. Contracts before implementation.
2. Capabilities over hard-coded workflows.
3. Provider-neutral interfaces.
4. Retrieval based on information requirements, not similarity alone.
5. Context treated as a controlled runtime resource.
6. Memory separated by purpose and lifecycle.
7. Least privilege for every tool and data source.
8. Evidence attached to every material decision.
9. Evaluation performed continuously.
10. Failure must be explicit, observable, and testable.
11. Human approval must be available for consequential operations.
12. Security controls must remain outside model discretion.

## 10. Version 1 Scope

Version 1 includes:

- One end-to-end analyst workflow
- Three registered analyst capabilities
- Four read-only tools
- Structured and unstructured retrieval
- Versioned prompt bundles
- Capability manifests
- Context budgeting
- Thread and workspace memory separation
- OPA/Rego-compatible policy decisions
- Offline benchmark execution
- Runtime trace generation
- Evidence bundle generation
- Security and tenant-isolation tests

## 11. Version 1 Non-Goals

Version 1 does not include:

- Autonomous write operations against production systems
- Unrestricted multi-agent collaboration
- Fine-tuning
- Kubernetes deployment
- Multi-region production deployment
- Model training
- Production customer data
- Unreviewed durable memory writes
- Direct model access to databases or internal APIs

## 12. Required Evidence

A completed workflow must produce evidence covering:

- Request identity and scope
- Selected capability and version
- Prompt versions
- Context policy
- Retrieved source identifiers
- Tool requests and results
- Policy decisions
- Model configuration
- Token consumption
- Cost estimate
- Latency
- Evaluation results
- Final output
- Human-review status, when applicable

## 13. Definition of Done

The initial vertical slice is complete when the system can:

1. Load a versioned capability manifest.
2. Validate an analyst request.
3. Select an approved context policy.
4. Retrieve authorized evidence.
5. Execute one typed read-only tool.
6. Compile a bounded context package.
7. Generate or simulate a schema-valid response.
8. evaluate the response.
9. Emit a complete trace.
10. Generate an evidence bundle.
11. Pass unit, integration, security, and isolation tests.

## 14. Current Status

**Current phase:** Phase 3 — Governed Retrieval and Context Engine

**Runtime authority:** None

**Production authority:** None

**Data classification:** Synthetic and demonstration data only

**Deployment status:** Not deployed

**Implementation status:** Versioned context policies, governed source metadata, deterministic information-requirement planning, tenant and workspace isolation, classification filtering, ranking, deduplication, token budgeting, provenance-rich context packages, insufficient-evidence controls, and read-only discovery APIs are implemented. Governed tools and MCP interoperability, memory, expanded evaluation, runtime approval controls, and external model integration remain pending.
