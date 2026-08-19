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
- Gate 3 child-runtime progress: `ExecutionRequest` binds `SkillManifest` identity to explicit capability grants; strict executable-skill mode requires a hardened backend; Linux/Bubblewrap adversarial probes verify host filesystem and outbound network isolation; HMAC receipt persistence, durable patch review, interrupted-run recovery and authenticated operator rollback binding are locally verified. Native Windows/macOS evidence remains open.
- Gate 4 progress: `MultiAgentWorkProductLoop` binds exclusive claims to typed work-product envelopes, per-agent snapshots, independent review, fresh-base authorization, explicit commit markers and durable resume/replay. MA-06 adds bounded retry/reclaim, cancellation non-retry, a 12-case cross-agent leakage corpus and deterministic quality metrics. MA-07 adds a three-lane parallel workload runner with injected crash/retry, SQLite/WAL result aggregation, completed-run replay and conflict rejection. MA-08 verifies crash injection before/after write/read and repeated mean/p50/p95 distributions. MA-09 verifies four simultaneous active-delegation sibling/path leakage probes; broader protocol/provider leakage remains open.
- Gate 5 progress: `MemoryQualityEvaluator` reports separate recall, attribution precision, conflict, temporal, compaction-retention, hard-budget, leakage-free and experience-reuse recall evidence from verifier/source IDs without model self-grading. `DurableMemoryQualityAdapter` now persists/reopens query-aware traces beside `Memory`; MEM-09 runs a real stdlib `Memory` + `ExperienceReuseSelector` trajectory over four persisted semantic facts with recall 0.75, attribution precision 1.0, reuse recall 1.0, budget compliance 1.0 and four reopened traces. Adversarial tests cover query/trace conflict, attribution leakage, budget violation, decay floor and restart persistence. The 64-token fixture distribution at scales 32/128/512/1024 over five repetitions remains baseline recall 0.0, nextgen recall 1.0, gain 1.0. Evidence schema is v2; this is deterministic local evidence, not an external model benchmark.
- Gate 6 preparation: fail-closed Windows PowerShell and macOS shell parity bundles now have a unified stdlib `validate_native_parity.py` CLI and `validate_native_artifacts` API. Matching-host validation rejects missing/malformed artifacts, guard violations, stale/non-passed parity results and SHA-256 manifest mismatches; ten native negative/contract cases pass locally. Matching-host execution remains `not_run`.
- External evidence readiness: duplicate receipt IDs across lanes and per-record protocol fingerprint mismatches against the manifest are now blocked; the current empty-pin matrix remains `not_run` with `native_or_external_execution_claim=false`.
- Pinned external workflow: `pinned_lane_orchestrator.py` now validates exact commit-shaped revisions, required lanes, seed digest, disposable workspace, deny-by-default network and positive budget policy before planning. Capability-aware inventory records required network/workspace/credential capabilities and executable availability without treating discovery as execution; missing or invalid prerequisites remain `not_run`/`blocked`.
- Approval boundary: `run_external_lane.py` now implements `noesis.external-approval.v1`, binding HMAC approval to exact plan identity with bounded expiry and persistent single-use receipt consumption. The receipt store uses transactional SQLite/WAL with one-winner concurrent consumption, reopen persistence and corruption fail-closed behavior. A durable execution journal records consumed/started/completed/abandoned states; interrupted or abandoned execution requires a new approval and completed execution is no-replay. Mutated plans, expired receipts, missing approval material and replayed receipts remain denied.
- 25%→100% claims roadmap: added `docs/ROADMAP_25_TO_100.md`, Russian supplemental localization and `docs/CLAIMS_PROGRESS_MATRIX.json`, separating local OS maturity from the much smaller proven-worldwide-leader evidence surface. Native and external claims remain explicitly host/pin gated.
- Track A operator surface: added read-only `/api/operator/snapshot` (`noesis.operator-snapshot.v1`) combining health, model capabilities, readiness, telemetry and operator context with recursive secret redaction; no tool/model execution is performed by the endpoint.
- Completion definition: the roadmap now explicitly has two stages—first complete the portable Python 3.14 Agent OS, then prove an evidence-backed leading/worldwide-superiority claim through native parity, pinned external A/B, independent scoring and review. The claims matrix records both stages and keeps superiority claims disabled.
- Governed self-learning: `EvaluatorRegistry` now exposes `noesis.evaluator-readiness.v1`; persisted evaluator manifests are not treated as runtime availability after restart, missing callable registrations are `blocked`, and matching re-registration is required before evaluation. Added restart/readiness regression coverage and synchronized English/Russian contracts.
- Track C memory quality: `MultiSessionMemoryQualityReport` and evidence schema v3 add durable three-session/six-case aggregation, cross-session experience reuse, decay-floor checks and reopen equality. The real-stdlib distribution reports aggregate recall 0.8333, attribution precision 1.0, reuse recall 1.0, budget compliance 1.0 and quality score 0.9792; broader independent corpora remain open.
- Python 3.14.7 full regression: 480 tests passed with `ResourceWarning` treated as an error; link, documentation security, JSON evidence, metadata and packaging consistency audits passed.
- Track D sandbox conformance: `run_conformance()` now combines command-level network/workspace/shell policy checks with a bounded workspace-write/process-exit probe for available backends; the v2 evidence artifact records Linux/Bubblewrap `passed` and macOS/Windows `not_run` on Linux. Added command-only backend rejection coverage and synchronized English/Russian roadmap contracts.
- Python 3.14.7 Track D validation: 482 tests passed with `ResourceWarning` treated as an error; link, documentation security, JSON evidence, metadata and packaging consistency audits passed.
- Track E portable artifacts: source-portable audit now excludes local runtime/build outputs, models, secrets, keys and archives; it emits a deterministic 415-file Python 3.14 ZIP with SPDX-2.3 SBOM and SHA-256 manifest, and verifier rejects traversal paths, coverage gaps and digest mismatches. Static artifact evidence remains separate from native Windows/macOS claims.
- Python 3.14.7 Track E validation: 483 tests passed with `ResourceWarning` treated as an error; link, documentation security, JSON evidence, metadata and packaging consistency audits passed.
- Track A operator workflow: `/api/operator/snapshot` now binds the authenticated operator session to bounded durable session context—state, task count, message count and event count—without exposing task/message content or adding execution side effects. English and Russian roadmaps are synchronized.
- Track B governed learning: proposals now carry a cryptographic provenance digest binding receipt facts, evaluation facts, skill name and content digest; approval and promotion reject stale or tampered provenance. Added bounded `noesis.learning-review-snapshot.v1` metadata and authenticated read-only `/api/learning/review`, which never exposes skill/payload content and fails closed when unavailable. Automatic activation remains disabled by default.
- Operator UI gate: the Cloudflare-style control-plane surface now includes a read-only Governed learning review panel with evaluator readiness, proposal count, provenance status and explicit disabled activation state. Claims matrix and English/Russian master plans now mark the operator workflow locally verified and set the next local gate to governed executable skill/tool runtime.
- Gate 3 execution assurance: recovery records now persist a canonical request fingerprint; terminal request replay is denied, mutated reuse of a run ID is rejected, signed receipt persistence is bound to a valid `completed`/`timed_out`/`denied`/`failed` recovery status, and local evidence is documented in `GATE3_EXECUTION_ASSURANCE_EVIDENCE.json`. Native and external execution remain explicitly `not_run`.
- Operator correlation gate: authenticated snapshot and telemetry/SSE now accept bounded `task_id`/`receipt_id` filters scoped to the configured operator session, expose deterministic lane lifecycle counters and preserve redacted durable receipt metadata. Filtered routes retain the same authentication boundary.
- Stage 2 protocol: added `INDEPENDENT_COMPARATIVE_SCORING_PROTOCOL.md` and its machine-readable JSON companion, with identity checks, deterministic dimensions, mandatory safety failures, readiness vocabulary and an explicit rule that local simulation cannot populate external competitor scores. Hermes, OpenCode and DeepSeek Harness remain `not_run` pending pinned executable environments.
- Stage 2 report builder: `external_evidence_readiness.py` now requires all three required lanes to pass before comparative readiness becomes true. Added provider-neutral `build_comparative_report.py` and `STAGE2_COMPARATIVE_REPORT_EVIDENCE.json`; signed evidence is verified first, while incomplete case-level evidence remains `score_available=false` and never produces a competitor score.
- Stage 2 case scoring: added signed `noesis.comparative-case-receipt.v1` ingestion with duplicate and tamper rejection, lane revision/protocol binding, complete corpus requirements, mandatory safety-failure blocking and deterministic per-lane/cross-lane dimension means. Local fixtures verify mechanics only; no external score is claimed.
- Operator case bundle: added deterministic `noesis.operator-case-bundle.v1` readiness-only export with manifest/bundle digests, fixed case IDs, lane readiness states, deny-by-default network, absent credentials, disposable workspace requirement and explicit `execution_allowed=false`/`automatic_execution=false`. Added English and Russian runbooks; no external command is invoked by bundle generation.
- Operator import validation: added `noesis.operator-import.v1` validator for bundle digest, manifest/case drift, required lane set, exact lane revision and protocol identity. Inconsistent input is `blocked`; consistent incomplete external evidence is `accepted_not_run`; import never sets `score_claim` or `external_execution_claim`.
- Operator import UI/SSE: authenticated read-only snapshot, telemetry and SSE now expose bounded import status and up to 32 drift reasons while forcibly retaining `score_claim=false` and `external_execution_claim=false`; the UI contains no import or provider-execution action.
- Operator artifact ingestion: added append-only `noesis.operator-ingestion.v1` SQLite/WAL lifecycle with `awaiting_approval`, signed short-lived approval, `imported`, `blocked` and `rejected` states. Import requires exact bundle/manifest identity, duplicate terminal imports are denied, and the ledger never executes providers or creates a comparative claim.
- Pinned-lane preflight: added static `noesis.external-lane-preflight.v1` checks for exact revisions, declared executable paths, deny-by-default network, absent credentials and disposable workspace policy. `ready_for_operator_approval` never means external execution; all execution and competitor scoring remain `not_run` until matching environments and explicit approval exist.

- Offline release audit remains claim-conservative: the synthetic private-key holdout fixture is intentional, while native target builds and external A/B remain unreleased gates; the pushed checkpoint tree is clean.
- Reconciled the normative English/Russian master roadmap, root roadmap navigation, self-learning maturity audit and operational checklist; bounded production lifecycle and durable promotion-state/evaluator deployment are locally verified, while governed executable child runtime is in progress with Linux-only isolation evidence.

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
