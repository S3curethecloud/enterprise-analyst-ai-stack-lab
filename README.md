
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
