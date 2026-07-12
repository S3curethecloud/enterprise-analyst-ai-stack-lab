
Phase 1 Demo Scenario — Deterministic Churn Analysis
Purpose

This scenario validates the first executable vertical slice of the Enterprise
Analyst AI Stack.

The phase intentionally uses deterministic execution and synthetic data so the
platform contracts, trace model, evidence structure, and API behavior can be
tested before introducing an external model provider.

Analyst Request

Explain why customer churn increased during Q2. Compare support incidents and
product usage, then provide an evidence-backed executive summary.

Runtime Flow
Validate the request contract.
Resolve tenant, workspace, and user identifiers.
Select the customer-churn-analysis capability identifier.
Create a deterministic context plan.
Load authorized synthetic evidence.
request the read-only customer metrics tool.
Evaluate the tool request through a deterministic policy decision.
execute the synthetic tool.
compile an evidence package.
generate deterministic findings and an executive summary.
validate the response schema.
evaluate groundedness and evidence coverage.
store the result and trace.
generate runtime evidence files.
Expected Decision
ALLOW
Expected Evaluation
PASS
Non-Goals

This phase does not provide:

External model invocation
Embedding generation
Vector retrieval
Dynamic capability registration
Durable database storage
Production authentication
Production authorization
Write-capable tools
