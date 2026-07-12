
Design Principles
1. Start With the Analytical Workflow

Model and framework selection follows the business workflow, data boundaries, risk classification, latency objective, cost budget, and operating model.

2. Capabilities Are Declarative

A standard analyst capability must be registered through manifests and contracts rather than implemented through new orchestration branches.

3. Prompts Are Versioned Artifacts

Prompts must be discoverable, immutable by version, testable, and linked to evaluation baselines.

Prompt strings must not be embedded directly in product application logic.

4. Tools Are Governed Interfaces

Tools must expose typed input and output schemas, required scopes, risk classifications, timeout limits, and side-effect declarations.

5. Context Is a Runtime Budget

Context construction must optimize for relevance, authorization, freshness, latency, cost, and evidence coverage.

Retrieval volume is not equivalent to context quality.

6. Metadata Is a Control Surface

Classification, ownership, lineage, tenant, freshness, geography, retention, and authorization metadata must influence retrieval and runtime decisions.

7. Memory Is Not One Store

Execution state, thread memory, workspace memory, user preferences, approved facts, and evidence history require separate lifecycles and policies.

8. Models Do Not Grant Themselves Authority

Authentication, authorization, policy enforcement, data filtering, durable writes, and consequential tool operations remain outside model discretion.

9. Evaluation Is Continuous

Prompt, retrieval, tool, context, memory, policy, and complete workflow behavior must be evaluated through repeatable benchmark suites.

10. Evidence Is a Product Output

Every material runtime decision must be traceable to its inputs, configuration, policy result, execution outcome, and evaluation evidence.

11. Fail Closed Where Authority Is Unclear

The runtime must return denial, redaction, insufficient evidence, restricted retry, or human escalation when authorization or evidence is inadequate.

12. Provider Dependencies Stay Behind Adapters

Product capabilities must not depend directly on one model provider, vector database, agent framework, or policy implementation.
