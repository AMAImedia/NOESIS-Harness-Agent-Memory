# Self-Learning, Agent Loop, OS Surface, and Documentation Sync Audit

**Audit date:** 2026-08-18  
**Repository:** `AMAImedia/NOESIS-Harness-Agent-Memory`  
**Verified commit:** `3a5e8c81867d3a80122e8d9f32b884a744b3aaad`

## Executive finding

NOESIS-Harness-Agent-Memory has a verified local-first agent operating system kernel and a bounded work-loop foundation. It does **not** yet implement a fully autonomous self-learning product loop comparable to a mature skill-creation system, and it does not yet provide native Windows/macOS or external competitor evidence.

The implementation is stronger than a prompt-only loop because sessions, tasks, leases, approvals, child-process control, provenance, recovery, SSE telemetry, and fail-closed evidence are represented in code and tests. However, the current agent loop is an execution primitive: it acquires a lease, invokes an injected action, persists an optional memory item, and returns a result. It is not yet a complete observe\u2192evaluate\u2192propose\u2192approve\u2192promote\u2192verify learning lifecycle.

## Gap matrix

| Capability | Status | Evidence or boundary |
|---|---|---|
| Agent action loop with lease ownership | `implemented / locally verified` | `noesis_harness/agent_loop.py`, coordination and multi-agent tests |
| Durable sessions/tasks and recovery | `implemented / locally verified` | Session/task APIs, SQLite event state, recovery and chaos tests |
| Memory tiers, provenance, confidence, decay and conflicts | `implemented / locally verified` | Memory/evidence/context/consolidation modules and focused tests |
| Experience reuse with scope and provenance checks | `implemented / locally verified` | `experience_reuse.py`, experience reuse tests |
| Multi-agent leases, signals, action dependencies and cancellation | `implemented / locally verified` | `coordination.py`, governance and multi-agent tests |
| Skill import/store/version/rollback safety | `implemented / bounded` | Import/store/rollback contracts exist; executable skill entrypoints remain intentionally disabled |
| Autonomous self-learning loop | `partial / not product-complete` | No complete evaluator-driven promotion loop, durable learned skill generation, or automatic verified skill activation |
| Human-approved learning promotion | `partial / contract-ready` | Governance and approval primitives exist; end-to-end learning proposal-to-promotion workflow remains a next implementation gate |
| OS/control plane: sessions, tasks, approvals, recovery | `implemented / locally verified` | Versioned command API and recovery evidence |
| OS/control plane: child runtime and sandbox | `implemented / Linux verified` | Bubblewrap/process control verified; Windows/macOS native lanes remain `not_run` |
| OS/control plane: SSE/operator telemetry | `implemented / locally verified` | `/api/telemetry`, `/api/child-runtimes`, bounded SSE dashboard |
| OS control plane: native Windows/macOS packaging | `source/static policy only` | Real `.exe`/`.app` builds require matching hosts and Python 3.14 native evidence |
| External Hermes/OpenCode/DeepSeek Harness execution | `not_run / blocked` | Exact revisions, executables and disposable approved environments are absent |
| English primary code/docs policy | `passed` | Primary code-facing scope is free of Cyrillic; English contracts are normative |
| Russian supplemental localization | `passed` | Localizations live under `docs/locales/ru/` and stale root paths are absent |
| Code/docs/GitHub synchronization | `passed at audit checkpoint` | Link, security, JSON evidence, release metadata and local/remote parity checks passed |

## What the OS already is

The project is a **local-first agent OS kernel/control plane**, not yet a complete cross-platform distribution. The verified kernel includes durable session and task state, explicit approval gates, event/state recovery, multi-agent coordination, isolated child-process primitives, Linux sandbox conformance, signed evidence ingestion, operator telemetry, and a portable/static packaging policy.

The project should not currently be described as a finished native Windows/macOS OS distribution, a fully autonomous self-improving agent platform, or a benchmark-proven superior system. Those claims require additional evidence listed below.

## Next implementation gate for self-learning

The highest-leverage remaining local gate is a **Human-Governed Learning Promotion Pipeline**:

1. Capture an experience record from a completed task with provenance, scope, policy context, and outcome receipt.
2. Run a deterministic evaluator against a holdout task set and record the evaluator version and evidence digest.
3. Produce a review-only learning proposal; do not modify active skills or durable policy automatically.
4. Require explicit approval and a scoped promotion decision.
5. Install an immutable skill/experience version transactionally with rollback support.
6. Re-run holdout, leakage, regression, and rollback tests before activation.
7. Emit a signed promotion receipt and expose the lifecycle through the operator telemetry surface.

Until this gate exists, current memory and experience reuse must be described as **provenance-aware reuse and governance primitives**, not as a complete self-learning loop.

## External and owner blockers

The remaining external gates are native Windows/macOS execution, exact pinned Hermes/OpenCode/DeepSeek Harness revisions and executable environments, and comparative A/B execution. Owner decisions remain required for the optional desktop wrapper, branch protection, native runners, and public release. No local simulation may promote these states to `passed`.
