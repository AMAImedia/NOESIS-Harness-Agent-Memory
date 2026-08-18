# Changelog

All notable changes to NOESIS-Harness-Agent-Memory are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Trust Plane provenance, lineage, Gatekeeper and child-runtime security closeout evidence.
- Versioned task/session command API, bounded SSE stream contract and approval-gated TaskExecutionBridge.
- SafeParallelExecutor with per-agent workspaces, durable Actions lifecycle and RecoveryCoordinator requeue.
- Portable artifact manifest/SBOM verifier and native Windows/macOS dry-run/signing-policy evidence lanes.
- Operator-owned migration mode source with HMAC-signed receipts persisted transactionally in the SQLite/WAL administrative audit store.
- Read-only `/api/audit/migration` endpoint and SSE/UI audit timeline rendering for the latest signed migration receipts.

### Changed
- Python 3.14 is the sole target runtime; CI packaging gates now verify portable SHA-256/SPDX coverage and both native target mismatch paths.

### Security
- Offline release audit is network-off-by-default and checks credential-like strings, AST eval/exec calls, package exports and clean Git state.

### Verification snapshot — 2026-08-18
- Python 3.14.7 full regression: 428 tests passed with `ResourceWarning` treated as an error; link, documentation security, JSON evidence, metadata, and packaging consistency audits passed.
- Offline release audit intentionally remains `clean: false` while the working tree contains this checkpoint and the synthetic private-key holdout fixture; native target builds and external A/B are still unreleased gates.
- Reconciled the normative English/Russian master roadmap, root roadmap navigation, self-learning maturity audit and operational checklist; bounded production learning lifecycle wiring is locally verified, and durable promotion-state/evaluator deployment is the next local gate.

## [0.5.0] - 2026-08-14

### Added
- MemoryGraph, ScopedMemory, Budget, HitlGate.
- ContextVfs (L0/L1/L2), extract_session, McpServer.
- benchmarks/recall20 (20/20).
- ALTER migrate for `memories.embedding` on old DBs.

### Changed
- README is self-contained for GitHub (no parent digest required).

## [0.4.0] - 2026-08-14

### Added
- Vector tier + configurable RRF fusion (optional backends; stdlib fallback).
- `PrivacyFilter`, snapshot export/import with LWW merge.
- `ConsolidationWorker`, `ProcedureRunner`.
- `Mesh` + HTTP snapshot peer; `InspectUI` (`noesis-inspect`).
- `AgentTrace` + `HybridJudge`.
- `DurableQueue` (WAL, dedup, retry, recover) and `LoopGuard`.
- Tests: 57+ stdlib unittest cases.

### Changed
- Package version 0.2.0 -> 0.4.0.

## [0.2.0] - 2026-08-14

### Added
- `docs/architecture.md`, `docs/api.md`, `docs/why.md` - full documentation suite.
- `examples/multi_agent_swarm.py` - 3 agents + coordination on a shared EventStore.
- `examples/memory_tiers.py` - 4-tier memory + decay + offload demo.
- `examples/dag_actions.py` - Actions DAG with typed edges + auto-unblock.
- `integrations/claude_code.py` - Claude Code bridge (local adapter, STUB).
- `integrations/codex.py` - OpenAI Codex CLI bridge (local adapter, STUB).
- `integrations/openclaw.py` - OpenClaw bridge + coordination (local adapter, STUB).
- `benchmarks/memory_bench.py` + `benchmarks/run_bench.py` - EventStore/Memory benchmarks.
- `.github/workflows/ci.yml` - CI on Python 3.9-3.12, examples, benchmarks, build, lint.
- `py.typed` marker for PEP 561.

### Changed
- `pyproject.toml` 0.1.0 -> 0.2.0; SPDX license expression; beta classifier.

## [0.1.0] - 2026-08-14

### Added
- `noesis_harness/event_store.py` - append-only JSONL + deterministic projection.
- `noesis_harness/memory.py` - 4-tier memory + FTS5 + decay + symbolic offload.
- `noesis_harness/coordination.py` - Leases (TTL), Signals (mailbox), Actions (DAG).
- `tests/test_core.py` - 15 stdlib tests (no deps).
- `examples/botfarm_lead.py` - worked example.
- README, AGENTS.md, LICENSE (MIT), pyproject.toml, .gitignore.

### Local development slice (not released)
- [x] Added stdlib-only `nextgen.py`: run envelopes, hash-chain audit, idempotent ledger, scoped agent broker, message-tree context and non-destructive compaction.
- [x] Added stdlib-only `governance.py`: capability Gatekeeper, DAG planner, Obsidian vault projection, staged skills and honest execution ladder.
- [x] Added 11 local tests and benchmark `benchmarks/nextgen_bench.py`; full suite passes locally.
- [ ] Remaining: durable fibers, richer memory conflict resolution, hardened subprocess/sandbox adapters and adversarial benchmark corpus.
