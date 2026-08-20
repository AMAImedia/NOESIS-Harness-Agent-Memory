# NOESIS-Harness-Agent-Memory documentation

This directory contains the technical documentation for the local-first NOESIS agent kernel.

> **Language policy:** English is the primary language for code, CLI and batch output, API contracts, schemas, tests, metadata, the root README and code-facing documentation. Russian is an additional localized layer; Russian documents use the `_RU.md` suffix. See [`LANGUAGE_POLICY.md`](LANGUAGE_POLICY.md).

| Document | Purpose |
|---|---|
| [`LANGUAGE_POLICY.md`](LANGUAGE_POLICY.md) | English-primary and Russian-supplemental language rules for code, docs, contracts and evidence. |
| [`LOCALIZATION_DUPLICATE_AUDIT.md`](LOCALIZATION_DUPLICATE_AUDIT.md) | Audit of locale structure, stale references, exact duplicates and primary-layer language boundaries. |
| [`RELEASE_AUDIT_EXTERNAL_READINESS.md`](RELEASE_AUDIT_EXTERNAL_READINESS.md) | Release-audit claim guard for the external readiness matrix and explicit local/private evidence boundary. |
| [`NATIVE_EVIDENCE_HONESTY_GATE.md`](NATIVE_EVIDENCE_HONESTY_GATE.md) | Local native-evidence verifier lanes with explicit target-host `not_run` semantics. |
| [`CROSS_PLATFORM_RELEASE_GATES.md`](CROSS_PLATFORM_RELEASE_GATES.md) | Aggregate local/native/external release gate matrix with fail-closed status and claim boundaries. |
| [`BUILD_POLICY_HONESTY_GATE.md`](BUILD_POLICY_HONESTY_GATE.md) | Native packaging dry-run, signing policy and target-host refusal semantics. |
| [`PARALLEL_AGENT_TRACKS.md`](PARALLEL_AGENT_TRACKS.md) | Evidence from isolated local reliability, security, operator and release audit tracks. |
| [`PARALLEL_AGENT_TRACKS_2.md`](PARALLEL_AGENT_TRACKS_2.md) | Second isolated run covering task/session, child-runtime, memory/governance and operator/release surfaces. |
| [`OPERATOR_TELEMETRY_DASHBOARD.md`](OPERATOR_TELEMETRY_DASHBOARD.md) | Read-only SSE and child-runtime telemetry dashboard contract with recursive redaction and bounded snapshots. |
| [`PARALLEL_STAGE4.md`](PARALLEL_STAGE4.md) | Repeatability, telemetry robustness and packaging/evidence honesty results from the fourth parallel stage. |
| [`SELF_LEARNING_OS_SYNC_AUDIT.md`](SELF_LEARNING_OS_SYNC_AUDIT.md) | Audit of self-learning maturity, agent work loops, OS/control-plane completeness and code/docs synchronization; Russian localization: [`SELF_LEARNING_OS_SYNC_AUDIT_RU.md`](locales/ru/SELF_LEARNING_OS_SYNC_AUDIT_RU.md). |
| [`LEARNING_PROMOTION_PIPELINE.md`](LEARNING_PROMOTION_PIPELINE.md) | Normative human-governed learning promotion lifecycle with deterministic holdout, explicit approval, immutable promotion, rollback and signed receipts; Russian localization: [`LEARNING_PROMOTION_PIPELINE_RU.md`](locales/ru/LEARNING_PROMOTION_PIPELINE_RU.md); machine evidence: [`LEARNING_PROMOTION_EVIDENCE.json`](LEARNING_PROMOTION_EVIDENCE.json). |
| [`LEARNING_PROMOTION_INTEGRATION.md`](LEARNING_PROMOTION_INTEGRATION.md) | Task completion, explicit evaluator registry and bounded review-only promotion telemetry integration; Russian localization: [`LEARNING_PROMOTION_INTEGRATION_RU.md`](locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md). |
| [`DURABLE_TURN_CHECKPOINTS.md`](DURABLE_TURN_CHECKPOINTS.md) | Crash-safe sequential per-turn persistence with SQLite/WAL, canonical SHA-256 checksums, recovery and corruption rejection; Russian localization: [`DURABLE_TURN_CHECKPOINTS_RU.md`](locales/ru/DURABLE_TURN_CHECKPOINTS_RU.md). |
| [`REAL_MEMORY_REUSE_STRESS.md`](REAL_MEMORY_REUSE_STRESS.md) | Real SQLite-backed memory reuse across repeated sessions and reopen boundaries with durable traces and deterministic distributions; Russian localization: [`REAL_MEMORY_REUSE_STRESS_RU.md`](locales/ru/REAL_MEMORY_REUSE_STRESS_RU.md). |
| [`GATE3_ARTIFACT_DIFF_RECEIPTS.md`](GATE3_ARTIFACT_DIFF_RECEIPTS.md) | Gate 3 child-runtime receipt contract with canonical before/after artifact manifests, signed diff binding, replay denial and recovery honesty; Russian localization: [`GATE3_ARTIFACT_DIFF_RECEIPTS_RU.md`](locales/ru/GATE3_ARTIFACT_DIFF_RECEIPTS_RU.md). |
| [`GATE3_RECOVERY_REPLAY.md`](GATE3_RECOVERY_REPLAY.md) | Authenticated recovery action contract with receipt-linked artifact diff, stale-state rejection, exact replay idempotency and rollback honesty; Russian localization: [`GATE3_RECOVERY_REPLAY_RU.md`](locales/ru/GATE3_RECOVERY_REPLAY_RU.md). |
| [`GATE3_TERMINAL_LIFECYCLE.md`](GATE3_TERMINAL_LIFECYCLE.md) | Durable execution-run terminalization with exact duplicate idempotency and fail-closed terminal conflicts; Russian localization: [`GATE3_TERMINAL_LIFECYCLE_RU.md`](locales/ru/GATE3_TERMINAL_LIFECYCLE_RU.md). |
| [`MULTI_AGENT_DELEGATION.md`](MULTI_AGENT_DELEGATION.md) | Capability-scoped delegated lanes with isolated workspaces, approval gates, artifact manifests and signed review-only receipts; Russian localization: [`MULTI_AGENT_DELEGATION_RU.md`](locales/ru/MULTI_AGENT_DELEGATION_RU.md). |
| [`PYTHON314_TEST_PERFORMANCE_PROFILE.json`](PYTHON314_TEST_PERFORMANCE_PROFILE.json) | Reproducible wall-time, peak tracemalloc and child RSS profile for the 382-test Python 3.14 suite. |
| [`SIGNED_EVIDENCE_FAIL_CLOSED.md`](SIGNED_EVIDENCE_FAIL_CLOSED.md) | Normative HMAC evidence envelope, hostile-input verification and fail-closed external A/B acceptance rules; Russian localization: [`SIGNED_EVIDENCE_FAIL_CLOSED_RU.md`](locales/ru/SIGNED_EVIDENCE_FAIL_CLOSED_RU.md). |
| [`EXTERNAL_EVIDENCE_READINESS.md`](EXTERNAL_EVIDENCE_READINESS.md) | Unified Hermes/OpenCode/DeepSeek Harness readiness statuses and acceptance checks; matrix artifact: [`EXTERNAL_EVIDENCE_READINESS_MATRIX.json`](EXTERNAL_EVIDENCE_READINESS_MATRIX.json); Russian localization: [`EXTERNAL_EVIDENCE_READINESS_RU.md`](locales/ru/EXTERNAL_EVIDENCE_READINESS_RU.md). |
| [`ARCHITECTURE_1.0_NEXTGEN.md`](ARCHITECTURE_1.0_NEXTGEN.md) | Architecture of run envelopes, capabilities, audit chains, durable fibers, evidence memory, coordination and bounded context. |
| [`EVALUATION_PROTOCOL.md`](EVALUATION_PROTOCOL.md) | Normative English evaluation criteria; Russian localization: [`EVALUATION_PROTOCOL_RU.md`](locales/ru/EVALUATION_PROTOCOL_RU.md). |
| [`IMPLEMENTATION_REPORT_2026-08.md`](IMPLEMENTATION_REPORT_2026-08.md) | Normative English implementation report; Russian localization: [`IMPLEMENTATION_REPORT_2026-08_RU.md`](locales/ru/IMPLEMENTATION_REPORT_2026-08_RU.md). |
| [`PLAN_NOESIS_1.0_MASTER.md`](PLAN_NOESIS_1.0_MASTER.md) | Normative English master plan; Russian localization: [`PLAN_NOESIS_1.0_MASTER_RU.md`](locales/ru/PLAN_NOESIS_1.0_MASTER_RU.md). |
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
| [`PROJECT_CHECKLIST_TODO_RU.md`](locales/ru/PROJECT_CHECKLIST_TODO_RU.md) | Shared Russian checklist/TODO with completed work, active tasks, owners, evidence, user approvals and the next action gate. |
| [`COMPETITOR_CAPABILITY_MAP_2026-08-18_RU.md`](locales/ru/COMPETITOR_CAPABILITY_MAP_2026-08-18_RU.md) | Source-grounded capability map for Hermes, OpenCode and Cloudflare Project Think; used for local gate selection, not superiority claims. |
| [`SKILL_DISCOVERY_CONTRACT_RU.md`](locales/ru/SKILL_DISCOVERY_CONTRACT_RU.md) | Read-only `SKILL.md` discovery, metadata validation, deterministic digest and explicit permission visibility contract. |
| [`EXPERIENCE_REUSE_CONTRACT_RU.md`](locales/ru/EXPERIENCE_REUSE_CONTRACT_RU.md) | Provenance-aware bounded experience reuse with scope/sensitivity denial, deterministic scoring and explainable budgets. |
| [`MULTI_AGENT_CANCELLATION_MERGE_GOVERNANCE_RU.md`](locales/ru/MULTI_AGENT_CANCELLATION_MERGE_GOVERNANCE_RU.md) | Cooperative cancellation/deadline contract, action recovery boundary and explicit independent-review merge authorization. |
| [`SANDBOX_BACKEND_CONFORMANCE_RU.md`](locales/ru/SANDBOX_BACKEND_CONFORMANCE_RU.md) | Linux/Bubblewrap and macOS sandbox backend contract, common conformance matrix, process boundary and native `not_run` semantics. |
| [`PROCESS_TREE_CANCELLATION_RU.md`](locales/ru/PROCESS_TREE_CANCELLATION_RU.md) | Process-group/job termination contract for non-cooperative children, timeout/recovery guarantees and native operator commands. |
| [`NEXT_HIGH_LEVERAGE_GATE_RU.md`](locales/ru/NEXT_HIGH_LEVERAGE_GATE_RU.md) | Cross-platform task-execution parity gate: native sandbox, task/session, memory/skill governance and pinned external evidence lanes. |
| [`TASK_EXECUTION_PARITY_RU.md`](locales/ru/TASK_EXECUTION_PARITY_RU.md) | Local end-to-end session/task → approval → child process → SSE → recovery smoke and explicit native/external `not_run` boundary. |
| [`PINNED_EXTERNAL_LANES_OPERATOR_RUNBOOK_RU.md`](locales/ru/PINNED_EXTERNAL_LANES_OPERATOR_RUNBOOK_RU.md) | Unified Linux/macOS/Windows operator bundle and pinned Hermes/OpenCode/DeepSeek Harness lane procedure with fail-closed `not_run` semantics. |
| [`ATTRIBUTION_SOURCE_NOTES_2026-08-18.md`](ATTRIBUTION_SOURCE_NOTES_2026-08-18.md) | Official source URLs and clean-room attribution boundaries for Cloudflare, Project Think, DeepSeek Harness, OpenClaw and Hermes. |
| [`UI_CONTRACT_V1.md`](UI_CONTRACT_V1.md) | Versioned stdlib-only boundary for health, models, errors, redaction and optional Hermes/DeepSeek adapters. |
| [`NATIVE_PACKAGING_RUNBOOK_RU.md`](locales/ru/NATIVE_PACKAGING_RUNBOOK_RU.md) | Windows/macOS native packaging, signing and target-host evidence runbook. |
| [`PARALLEL_RELEASE_AUDIT_RU.md`](locales/ru/PARALLEL_RELEASE_AUDIT_RU.md) | Offline release audit, secret/AST/export/Git cleanliness gates. |
| [`PARALLEL_CI_CONSISTENCY_RU.md`](locales/ru/PARALLEL_CI_CONSISTENCY_RU.md) | CI/runbook consistency and portable artifact evidence. |
| [`PARALLEL_DOCUMENTATION_EVIDENCE_RU.md`](locales/ru/PARALLEL_DOCUMENTATION_EVIDENCE_RU.md) | Markdown security, local-link and JSON schema evidence. |
| [`PARALLEL_LOCAL_SAFETY_EVIDENCE_RU.md`](locales/ru/PARALLEL_LOCAL_SAFETY_EVIDENCE_RU.md) | Local patch/recovery, capability denial, credential holdout and approval-bypass metrics; simulation-only boundary. |
| [`third_party_provenance.json`](third_party_provenance.json) | Machine-readable upstream reference/license/provenance manifest. |
