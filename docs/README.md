# NOESIS-Harness-Agent-Memory documentation

This directory contains the technical documentation for the local-first NOESIS agent kernel.

| Document | Purpose |
|---|---|
| [`ARCHITECTURE_1.0_NEXTGEN.md`](ARCHITECTURE_1.0_NEXTGEN.md) | Architecture of run envelopes, capabilities, audit chains, durable fibers, evidence memory, coordination and bounded context. |
| [`EVALUATION_PROTOCOL.md`](EVALUATION_PROTOCOL.md) | Reproducible criteria for memory, coordination, security, coding tasks and release decisions. |
| [`IMPLEMENTATION_REPORT_2026-08.md`](IMPLEMENTATION_REPORT_2026-08.md) | Verified local implementation report and benchmark snapshot dated 2026-08-17. |
| [`PLAN_NOESIS_1.0_MASTER.md`](PLAN_NOESIS_1.0_MASTER.md) | Master implementation plan and phase gates. |
| [`api.md`](api.md) | Existing API notes for the core package. |
| [`architecture.md`](architecture.md) | Earlier architecture notes retained for historical context. |
| [`why.md`](why.md) | Motivation and design rationale. |
| [`recipes/`](recipes/) | Focused examples for DAG actions, event sourcing, human-in-the-loop governance, memory tiers and multi-agent work. |

The repository is currently maintained in a **private GitHub repository**. Documentation is written for safe review; public visibility and publication remain owner-approved gates.

## Security boundary

The deterministic core is stdlib-only and does not execute model-generated Python in-process. It provides capability decisions, auditability, logical private scopes and fail-soft execution status. It does **not** claim to replace an operating-system sandbox, VM, container or hardened remote execution service. The execution ladder returns `unavailable` when such an adapter is not configured.

## Sources

The design references [Cloudflare OS](https://github.com/cloudflare/cloudflare-os) and [Project Think](https://blog.cloudflare.com/project-think/) for capability-based access, durable execution, sub-agent isolation, persistent sessions and execution ladders. NOESIS implements a local Python/SQLite interpretation of selected principles rather than copying or depending on the Cloudflare runtime. Hermes WebUI, DeepSeek Harness and DSH Desktop are treated similarly: reference implementations and optional adapter targets, not mandatory dependencies of the deterministic core.

| [`ARXIV_2608_13417_DECISION_MEMO.md`](ARXIV_2608_13417_DECISION_MEMO.md) | Decision memo applying the long-horizon process, experience-reuse and harness-evaluation findings from arXiv:2608.13417. |
| [`PORTABLE_UI_INTEGRATION_ROADMAP.md`](PORTABLE_UI_INTEGRATION_ROADMAP.md) | Verified plan for an optional Windows/macOS Portable Control Plane, model/provider adapters, safe skill bundles and Hermes/DeepSeek bridge boundaries. |
| [`PROJECT_CHECKLIST_TODO_RU.md`](PROJECT_CHECKLIST_TODO_RU.md) | Shared Russian checklist/TODO with completed work, active tasks, owners, evidence, user approvals and the next action gate. |
| [`COMPETITOR_CAPABILITY_MAP_2026-08-18_RU.md`](COMPETITOR_CAPABILITY_MAP_2026-08-18_RU.md) | Source-grounded capability map for Hermes, OpenCode and Cloudflare Project Think; used for local gate selection, not superiority claims. |
| [`SKILL_DISCOVERY_CONTRACT_RU.md`](SKILL_DISCOVERY_CONTRACT_RU.md) | Read-only `SKILL.md` discovery, metadata validation, deterministic digest and explicit permission visibility contract. |
| [`EXPERIENCE_REUSE_CONTRACT_RU.md`](EXPERIENCE_REUSE_CONTRACT_RU.md) | Provenance-aware bounded experience reuse with scope/sensitivity denial, deterministic scoring and explainable budgets. |
| [`MULTI_AGENT_CANCELLATION_MERGE_GOVERNANCE_RU.md`](MULTI_AGENT_CANCELLATION_MERGE_GOVERNANCE_RU.md) | Cooperative cancellation/deadline contract, action recovery boundary and explicit independent-review merge authorization. |
| [`SANDBOX_BACKEND_CONFORMANCE_RU.md`](SANDBOX_BACKEND_CONFORMANCE_RU.md) | Linux/Bubblewrap and macOS sandbox backend contract, common conformance matrix, process boundary and native `not_run` semantics. |
| [`UI_CONTRACT_V1.md`](UI_CONTRACT_V1.md) | Versioned stdlib-only boundary for health, models, errors, redaction and optional Hermes/DeepSeek adapters. |
| [`NATIVE_PACKAGING_RUNBOOK_RU.md`](NATIVE_PACKAGING_RUNBOOK_RU.md) | Windows/macOS native packaging, signing and target-host evidence runbook. |
| [`PARALLEL_RELEASE_AUDIT_RU.md`](PARALLEL_RELEASE_AUDIT_RU.md) | Offline release audit, secret/AST/export/Git cleanliness gates. |
| [`PARALLEL_CI_CONSISTENCY_RU.md`](PARALLEL_CI_CONSISTENCY_RU.md) | CI/runbook consistency and portable artifact evidence. |
| [`PARALLEL_DOCUMENTATION_EVIDENCE_RU.md`](PARALLEL_DOCUMENTATION_EVIDENCE_RU.md) | Markdown security, local-link and JSON schema evidence. |
| [`PARALLEL_LOCAL_SAFETY_EVIDENCE_RU.md`](PARALLEL_LOCAL_SAFETY_EVIDENCE_RU.md) | Local patch/recovery, capability denial, credential holdout and approval-bypass metrics; simulation-only boundary. |
| [`third_party_provenance.json`](third_party_provenance.json) | Machine-readable upstream reference/license/provenance manifest. |
