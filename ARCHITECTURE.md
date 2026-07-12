# Enterprise Analyst AI Stack — Reference Architecture

## Architecture Objective

The Enterprise Analyst AI Stack provides reusable abstractions for prompts, tools, metadata, context, memory, evaluation, policy, and runtime evidence.

The system separates product-specific analytical capabilities from the shared AI runtime.

## Logical Architecture

```mermaid
flowchart TB
    U[Analyst or Product Application]

    subgraph Experience["Analyst Experience Layer"]
        UI[Analyst UI]
        API[REST API]
        REVIEW[Human Review Console]
    end

    subgraph Gateway["AI Gateway"]
        AUTH[Authentication and Identity]
        VALIDATE[Request Validation]
        TENANT[Tenant and Workspace Resolution]
        RISK[Risk Classification]
        ROUTE[Capability Routing]
    end

    subgraph Control["Capability Control Plane"]
        CAPREG[Capability Registry]
        PROMPTREG[Prompt Registry]
        TOOLREG[Tool Registry]
        CONTEXTPOL[Context Policies]
        MEMPOL[Memory Policies]
        EVALBIND[Evaluation Bindings]
        SCHEMAS[Output Schemas]
    end

    subgraph Runtime["Analyst Runtime"]
        CLASSIFY[Task Classifier]
        PLAN[Context Planner]
        GRAPH[Execution Graph]
        SYNTH[Synthesizer]
        VERIFY[Response Verifier]
    end

    subgraph Context["Context and Retrieval Plane"]
        REWRITE[Query and Requirement Expansion]
        RETRIEVE[Hybrid Retrieval]
        FILTER[Metadata and Authorization Filters]
        RERANK[Reranking]
        COMPRESS[Context Compression]
        BUDGET[Token Budgeting]
    end

    subgraph Tools["Governed Tool Gateway"]
        TOOLAUTH[Tool Authorization]
        TOOLSCHEMA[Schema Validation]
        TOOLPOLICY[Policy Evaluation]
        EXECUTE[Tool Execution]
        PROVENANCE[Result Provenance]
    end

    subgraph Data["Enterprise Data Plane"]
        DOCS[Documents]
        VECTOR[Vector Index]
        SQL[Structured Data]
        CATALOG[Metadata Catalog]
        LINEAGE[Lineage and Classification]
    end

    subgraph Memory["Memory and State Plane"]
        THREAD[Thread State]
        WORKSPACE[Workspace Memory]
        PREFS[User Preferences]
        FACTS[Approved Facts]
    end

    subgraph Trust["Trust, Evaluation and Evidence Plane"]
        POLICY[Policy Engine]
        EVAL[Evaluation Runner]
        BENCH[Benchmark Registry]
        TRACE[OpenTelemetry Traces]
        LEDGER[Evidence Ledger]
    end

    U --> Experience
    UI --> API
    API --> AUTH
    AUTH --> VALIDATE
    VALIDATE --> TENANT
    TENANT --> RISK
    RISK --> ROUTE

    ROUTE --> CAPREG
    CAPREG --> PROMPTREG
    CAPREG --> TOOLREG
    CAPREG --> CONTEXTPOL
    CAPREG --> MEMPOL
    CAPREG --> EVALBIND
    CAPREG --> SCHEMAS

    CAPREG --> CLASSIFY
    CLASSIFY --> PLAN
    PLAN --> GRAPH
    GRAPH --> Context
    GRAPH --> Tools
    GRAPH --> Memory

    RETRIEVE --> DOCS
    RETRIEVE --> VECTOR
    RETRIEVE --> SQL
    FILTER --> CATALOG
    FILTER --> LINEAGE

    TOOLPOLICY --> POLICY
    GRAPH --> SYNTH
    SYNTH --> VERIFY
    VERIFY --> EVAL
    VERIFY --> REVIEW

    Runtime --> TRACE
    Context --> TRACE
    Tools --> TRACE
    Memory --> TRACE
    POLICY --> LEDGER
    EVAL --> LEDGER
    TRACE --> LEDGER
Primary Runtime Flow
sequenceDiagram
    participant A as Analyst
    participant G as AI Gateway
    participant C as Capability Registry
    participant R as Analyst Runtime
    participant X as Context Engine
    participant P as Policy Engine
    participant T as Tool Gateway
    participant E as Evaluation Service
    participant L as Evidence Service

    A->>G: Submit analytical request
    G->>G: Authenticate and resolve tenant
    G->>C: Resolve capability
    C-->>G: Capability manifest and versions
    G->>R: Start governed execution
    R->>X: Build context plan
    X->>P: Authorize data sources
    P-->>X: ALLOW, DENY, or REDACT
    X-->>R: Context package with provenance
    R->>T: Request typed tool execution
    T->>P: Authorize tool and arguments
    P-->>T: Policy decision
    T-->>R: Tool result with provenance
    R->>R: Generate structured analysis
    R->>E: Evaluate result and trace
    E-->>R: Evaluation scores
    R->>L: Create evidence bundle
    R-->>A: Evidence-backed response
Core Platform Interfaces

The runtime will depend on stable interfaces rather than provider-specific SDKs.

class ModelGateway:
    async def generate(self, request):
        raise NotImplementedError


class RetrievalProvider:
    async def retrieve(self, request):
        raise NotImplementedError


class ToolProvider:
    async def execute(self, request):
        raise NotImplementedError


class MemoryProvider:
    async def read(self, request):
        raise NotImplementedError

    async def write(self, request):
        raise NotImplementedError


class PolicyProvider:
    async def evaluate(self, request):
        raise NotImplementedError


class EvaluationProvider:
    async def evaluate(self, request):
        raise NotImplementedError
Capability Abstraction

A capability binds together:

Supported task types
Prompt versions
Allowed tools
Context strategy
Memory policy
Evaluation suite
Output schema
Runtime limits
Risk classification

The core runtime must not contain capability-specific prompt text or tool logic.

Security Model

The platform enforces:

User and workload identity
Tenant isolation
Workspace isolation
Source-level authorization
Tool-level authorization
Input and output schema validation
Explicit side-effect classification
Durable-memory write controls
Prompt-injection defenses
Evidence and audit capture
Human approval for consequential actions
Deployment Evolution
Local Lab
FastAPI
PostgreSQL and pgvector
Redis
OPA
OpenTelemetry collector
Docker Compose
Cloud Reference Deployment

The platform may later map to managed cloud services, but cloud-provider implementation is not part of the first vertical slice.

The architecture must remain portable across AWS, Azure, GCP, hosted model APIs, and approved local model runtimes.
