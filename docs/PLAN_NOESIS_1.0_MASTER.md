# NOESIS 1.0 Master Plan

**Status checkpoint:** 2026-08-25, governed learning review UI checkpoint
**Runtime policy:** Python 3.14 only; deterministic core is stdlib-only.
**Operating model:** local-first, private-by-default, human-governed, fail-closed.

This is the normative English roadmap. The weighted 25%→100% execution plan is [`ROADMAP_25_TO_100.md`](ROADMAP_25_TO_100.md), with machine-readable claim status in [`CLAIMS_PROGRESS_MATRIX.json`](CLAIMS_PROGRESS_MATRIX.json). The completion target is two-stage: first deliver a genuinely complete, portable Python 3.14 Agent OS; then establish an evidence-backed leading/worldwide-superiority claim through native parity, pinned external A/B, independent scoring, reproducibility and review. This document remains a delivery plan, not a superiority claim.

## Current verified baseline

| Surface | Status | Evidence boundary |
|---|---|---|
| Memory, provenance, decay, conflicts, retrieval and bounded experience reuse | `passed / local` | Deterministic unit and adversarial tests; no claim of universal memory superiority |
| Durable sessions, task API, leases, cancellation, recovery and resume | `passed / local` | Python 3.14 regression and chaos/recovery tests |
| Multi-agent coordination and private-scope controls | `passed / bounded local` | Leakage, scope, duplicate-delivery and governance tests |
| Human-governed learning promotion | `passed / bounded local` | Receipt, evaluator, review proposal, approval, immutable version, rollback and signed evidence contracts; executable activation remains separately gated |
| Administrative SQLite/WAL migration and signed mode audit | `passed / local` | Transactional state/audit persistence, dual-read guard, rollback, HealthServer readiness and UI/SSE timeline |
| Child execution and Linux/Bubblewrap isolation | `passed / Linux local` | Conformance and fail-closed tests; native target parity is not inferred |
| Operator control plane and Cloudflare-style read-only telemetry UI | `passed / local` | Health, readiness, audit, child-runtime, bounded SSE and session-context snapshot contracts |
| Windows/macOS native sandbox and packaging | `not_run / host required` | Static manifests and refusal policy exist; no native evidence is claimed |
| Hermes/OpenCode/DeepSeek Harness external A/B | `not_run / pinned environment required` | Readiness and signed-ingestion contracts exist; no external process result is claimed |

## Remaining delivery gates

### Gate 1 — Bounded production learning lifecycle binding (current checkpoint)

The bounded production binding is now implemented: `ProductionLearningLifecycle` composes the durable task store, terminal-event bridge, runtime-owned policy simulator and explicit operator action executor. The portable launcher wires this composition to HealthServer only when a valid signing key is explicitly configured. The authenticated read-only `/api/learning/review` endpoint and Cloudflare-style UI panel now expose bounded proposal/evaluator metadata, provenance status and disabled activation state without content or execution side effects. The path remains explicit:

`terminal task -> provenance receipt -> deterministic holdout -> review proposal -> independent approval -> immutable promotion -> verification -> signed receipt -> optional activation`.

The local facade gate is verified by positive, negative, replay and activation-boundary tests. A task completion event never silently evaluates, approves, promotes or activates a skill. Durable promotion/evaluator state, provenance-bound proposals and the bounded operator review workflow are locally verified. Remaining work is the separately governed executable skill/tool runtime and broader independent learning corpora.

### Gate 2 — Durable promotion state and evaluator deployment (completed local gate)

Implemented and verified: promotion receipts, evaluations, proposals, previous-active metadata and evaluator manifests persist in SQLite/WAL; reopened pipelines reconstruct bounded state; identical retries are idempotent; payload/content/manifest conflicts fail closed; `PromotionIntegration.snapshot()` exposes bounded counts and manifest digests to HealthServer/UI/SSE. Automatic activation remains disabled. Full Python 3.14 validation passed with 430 tests.

### Gate 3 — Governed executable skill/tool runtime (in progress)

The manifest/grant contract and Linux reference path are implemented: `ExecutionRequest` binds an optional `SkillManifest` to explicit granted capabilities; strict executable-skill mode requires an available hardened backend; `BubblewrapBackend` provides the Linux namespace/network/filesystem boundary. The backend-neutral `run_conformance()` contract now adds a bounded workspace-write/process-exit probe after command-level policy checks, while unavailable or command-only backends remain `not_run`/failed rather than being treated as passed. HMAC-signed `ExecutionReceiptStore`, restart-safe `ExecutionRecoveryStore` and durable `PatchReviewStore` now cover result evidence, interrupted-run state and review status. The parent control plane never imports or executes model-generated code. Windows and macOS backends remain conformance targets until run on matching hosts.

Acceptance requires path escape, network egress, credential-like output, environment poisoning, symlink, timeout, process-tree, corrupted receipt, interrupted write, receipt replay/tamper, patch-review conflict, authenticated rollback, stale-base and cross-agent workspace tests. The local Gate 3 subgates are now covered: `ExecutionRecoveryExecutor` requires authenticated operator context, signed receipt/run identity, approved patch, fresh base and an injected handler that confirms the actual mutation. Unconfigured or unverifiable backends must return `not_run`, `blocked` or `unavailable`, never `passed`.

### Gate 4 — Real multi-agent work product loop (in progress)

`MultiAgentWorkProductLoop` binds exclusive task claims to typed `WorkProductEnvelope` records, per-agent workspace snapshots, independent review, fresh-base merge authorization, explicit task commit markers and durable session resume/replay. `SafeParallelExecutor` now supports an explicit retry limit with action reclaim while cancellation is never retried. The fixed cross-agent leakage corpus contains 12 deterministic holdouts, and `WorkProductBenchmarkEvaluator` reports separate correctness, delivery, leakage, recovery, reviewer-time, retry and commit metrics. MA-07 now provides a local deterministic workload runner with multiple parallel lanes, injected first-attempt crash, bounded retry/reclaim, durable SQLite/WAL result aggregation, completed-run replay and aggregation conflict rejection. MA-08 now covers crash injection before write, after write and after read, active-lane workspace escape probes, repeated runs with deterministic mean/p50/p95 reporting and bounded repetition count. MA-09 now adds four simultaneous active-delegation probes for sibling read/write, absolute path and traversal denial. Gate 4 local leakage evidence is bounded-local verified; broader protocol/provider leakage and external/native comparison remain open. A durable commit-marker ledger is now bound into `MultiAgentWorkProductLoop.commit/resume`, and the protocol-leakage holdout suite v1, including negative foreign-marker injection cases, is locally verified; native/external lanes remain `not_run`.

### Gate 5 — Memory and long-context quality evidence (in progress)

`MemoryQualityEvaluator` now reports separate recall, attribution precision, conflict-resolution rate, temporal-order rate, compaction retention, hard budget compliance, leakage-free rate and experience-reuse recall. `DurableMemoryQualityAdapter` records verified traces beside the real `Memory` store in SQLite/WAL and reloads them after restart, including query identity and reuse provenance. MEM-09 now includes `MultiSessionMemoryQualityReport` and a deterministic real-stdlib distribution over three durable sessions and six cases, with cross-session experience reuse, real `Memory.recall`, durable observations, temporal decay-floor checks and reopened aggregate equality: aggregate recall mean 0.8333, attribution precision 1.0, reuse recall 1.0, budget compliance 1.0 and quality score 0.9792. Adversarial coverage includes query/trace conflict, attribution leakage, hard-budget violation, empty-session rejection, decay floor and restart persistence. The 64-token fixture distribution at scales 32/128/512/1024 over five repetitions remains: baseline recall mean 0.0, nextgen recall mean 1.0, gain 1.0. This is deterministic local evidence, not an external model benchmark. Evidence schema is v3. The adversarial memory-quality corpus v2 is additionally wired into `scripts/run_memory_quality_evidence.py` as an additive `adversarial_corpus_v2` key, with the regenerated `docs/MEMORY_QUALITY_EVIDENCE.json` remaining byte-stable. Gate 6 preparation includes fail-closed native Windows/macOS bundles and runbooks; target execution remains `not_run` until matching hosts.

### Gate 6 — Native Windows/macOS evidence

Run the same operator bundle and parity contract on matching Windows and macOS hosts with Python 3.14. The operator bundle now has a single stdlib CLI validator that rejects host mismatch, missing or malformed artifacts, failed network/credential guards, non-passed parity results, incomplete SBOM entries, empty manifests and SHA-256 mismatches. The source-portable audit builds and verifies a 415-file Python 3.14 ZIP with SPDX-2.3 inventory and SHA-256 coverage, excluding local runtime/build outputs, models, secrets, keys and archive directories; traversal paths are rejected. Produce environment digests, backend conformance receipts, packaging manifests, SHA-256/SBOM records and negative-path results. Local tests cover native contract and artifact negative cases; until matching-host execution occurs, statuses remain `not_run`.

### Gate 7 — Pinned external A/B evidence

Acquire exact immutable revisions and executable environments for Hermes, OpenCode and DeepSeek Harness. The pinned orchestrator now validates exact commit-shaped revisions, required external lane coverage, seed digest when required, disposable workspace policy, deny-by-default network and budget policy before planning a lane. Its capability-aware inventory records required network/workspace/credential capabilities and executable availability without treating discovery as execution. Use disposable workspaces, a connector-neutral task protocol, identical task corpus, fixed budgets, independent scoring, signed evidence receipts and `noesis.external-approval.v1` receipts bound to exact plan identity. Approval receipts have bounded expiry and persistent single-use replay protection; mutated argv, revision, workspace, protocol fingerprint or task-manifest identity is rejected. Compare correctness, evidence quality, recovery, isolation, approval bypass, credential leakage, latency, reviewer time and resource use. Missing or mismatched environments remain `not_run` or `blocked`.

### Gate 8 — Release and public-claim review

Only after Gates 1–7 produce evidence may the project consider a public release claim. Run full Python 3.14 tests, link/schema/security audits, reproducibility checks, clean-tree release audit, license/provenance review and documentation localization audit. The public README must state both verified capabilities and unresolved boundaries.

## Execution order and synchronization rule

The next work sequence is: **(1) harden and verify the governed executable skill/tool runtime, (2) update code/docs/evidence in one focused change, (3) run full validation, commit and verify the private remote, (4) bind the end-to-end multi-agent work-product loop, (5) measure memory quality gates, and only then run native/external lanes**. No new gate is considered complete until code, tests, English primary documentation, Russian supplemental documentation and machine-readable evidence agree.

## Honest completion criterion

“Best in the world” is not a current project status. It becomes a testable hypothesis only when the same pinned tasks and environments show a statistically and operationally meaningful advantage without weakening safety, provenance, recovery or human control. Until that point, the correct description is **a local-first, provenance-aware and human-governed agent OS kernel with a verified Linux control plane and explicit native/external readiness gates**.

Russian supplemental localization: [`PLAN_NOESIS_1.0_MASTER_RU.md`](locales/ru/PLAN_NOESIS_1.0_MASTER_RU.md).

Related contracts: [`LEARNING_PROMOTION_PIPELINE.md`](LEARNING_PROMOTION_PIPELINE.md), [`GATE3_EXECUTION_ASSURANCE.md`](GATE3_EXECUTION_ASSURANCE.md), [`CROSS_PLATFORM_RELEASE_GATES.md`](CROSS_PLATFORM_RELEASE_GATES.md), [`EXTERNAL_EVIDENCE_READINESS.md`](EXTERNAL_EVIDENCE_READINESS.md), and [`SIGNED_EVIDENCE_FAIL_CLOSED.md`](SIGNED_EVIDENCE_FAIL_CLOSED.md).

## References

[1]: https://github.com/cloudflare/cloudflare-os "Cloudflare OS"
[2]: https://github.com/NousResearch/hermes-agent "Hermes Agent"
[3]: https://github.com/opencode-ai/opencode "OpenCode"
[4]: https://github.com/deepseek-ai/DeepSeek-V3 "DeepSeek public model reference; external harness status remains environment-gated"
[5]: https://arxiv.org/abs/2608.13417 "arXiv:2608.13417"

The upstream projects and paper are design references and benchmark targets, not evidence that NOESIS has executed or surpassed them.

## Claim boundary

Cloudflare OS, Hermes, OpenCode, DeepSeek Harness and other systems are treated as external references or optional adapter targets. Their code is not silently assumed to be incorporated, their licenses do not remove attribution obligations, and their capabilities are not counted as NOESIS evidence until the corresponding local implementation or signed external run exists.
