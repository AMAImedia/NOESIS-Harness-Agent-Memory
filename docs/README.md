# NOESIS documentation index

This directory holds the technical documentation for the local-first NOESIS agent
kernel. English is the primary language for code, CLI, API contracts, schemas,
tests, metadata and code-facing docs. Russian is an additional localized layer
using the `_RU.md` suffix (see [LANGUAGE_POLICY.md](LANGUAGE_POLICY.md)).

The repository previously accumulated many per-wave decision memos and audit
reports. Those are preserved under `_archive/` (never deleted); the working set
below is the curated minimum needed to operate and extend the project.

| Document | Purpose |
|---|---|
| [README.md](../README.md) | Repo entry point, quick start, honesty boundary. |
| [AGENTS.md](../AGENTS.md) | Hard rules for AI coding agents (zero-dep core, append-only, idempotent, tests with every change). |
| [ROADMAP_25_TO_100.md](ROADMAP_25_TO_100.md) | Plan, tracks A/B/C, milestones and landed-evidence log. |
| [RELEASE_REVIEW_CHECKLIST.md](RELEASE_REVIEW_CHECKLIST.md) | Release review procedure (stages 1-10). |
| [RELEASE_REVIEW_STATUS_2026-08-27.md](RELEASE_REVIEW_STATUS_2026-08-27.md) | Current per-stage status and honest blockers. |
| [ADDON_TSEARCH_BRIDGE.md](ADDON_TSEARCH_BRIDGE.md) | Optional t-search-harness retrieval lens over NOESIS memory. |
| [architecture.md](architecture.md) | Core architecture and event-sourced projection model. |
| [api.md](api.md) | API notes for the core package. |
| [LANGUAGE_POLICY.md](LANGUAGE_POLICY.md) | English-primary / Russian-supplemental language rules. |
| [MODEL_TASK_SANDBOX_DESIGN.md](MODEL_TASK_SANDBOX_DESIGN.md) | Model-task sandbox, proxy-jail and AppContainer design. |
| [NATIVE_PACKAGING_RUNBOOK.md](NATIVE_PACKAGING_RUNBOOK.md) | Windows/macOS native packaging, signing and target-host evidence runbook. |
| [third_party_provenance.json](third_party_provenance.json) | Machine-readable upstream reference/license/provenance manifest. |

## Security boundary
The deterministic core is stdlib-only and does not execute model-generated
Python in-process. It provides capability decisions, auditability, logical
private scopes and fail-soft execution status. It does NOT replace an OS sandbox,
VM, container or hardened remote execution service; the execution ladder returns
`unavailable` when such an adapter is not configured.

## Honesty gate
Status vocabulary is stable and English: `passed`, `failed`, `blocked`,
`not_run`, `not_started`, `unknown`. A `not_run`/`blocked` lane is an honest
statement of missing host/credentials, never a failure disguised as success.

## Sources
Design references Cloudflare OS / Project Think, LoopX, agentmemory, TencentDB,
deepseek-harness, Hermes and agent-teams as patterns. NOESIS implements a local
Python/SQLite interpretation of selected principles, not a copy or dependency.
