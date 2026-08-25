# NOESIS 25%→100% Claim-Ready Roadmap

**Status:** Baseline frozen at approximately **25–35% of the evidence required for a defensible “best in the world” claim**. The local control-plane implementation is substantially further along than the external proof surface. The roadmap has a two-stage completion target: **complete the portable Python 3.14 Agent OS first, then prove the worldwide-leading claim**. This document is an execution roadmap, not a superiority claim.

## 1. Progress model

The project uses weighted evidence rather than feature counting. A feature is not considered complete until its implementation, adversarial tests, machine-readable evidence, documentation and reproducibility boundary agree.

| Milestone | Evidence target | Required outcome |
|---|---:|---|
| 25% | Local governed kernel | Durable sessions, memory, approvals, multi-agent coordination, Linux isolation and recovery are locally verified |
| 40% | Integrated local OS | Control plane, operator telemetry, governed learning lifecycle, child-runtime contracts and work-product loop are integrated |
| 55% | Hardened local release candidate | Non-fixture memory/agent stress, chaos/recovery, leakage holdouts, artifact integrity and portable packaging are reproducible |
| 70% | Native-ready release candidate | Matching Windows/macOS bundles produce verified parity evidence; Linux preparation is not substituted for native execution |
| 85% | Comparative-ready system | Exact pinned Hermes/OpenCode/DeepSeek environments, identical tasks, signed receipts and independent scoring are available |
| 100% | Complete Agent OS plus claim-ready evidence package | Portable Agent OS contract is complete, then repeated external A/B results show meaningful advantage without safety, provenance, recovery or human-control regression; release audit passes |

## 2. Parallel execution tracks

### Track A — Control plane and operator surface

Complete versioned task/session command APIs, interactive chat/streaming contracts, durable SSE telemetry, child-runtime state views, operator approvals, diff/patch review, per-agent workspaces and session resume. The read-only `/api/operator/snapshot` contract now combines health, model capability, readiness, telemetry, authenticated operator-context metadata and bounded session context (state, task count, message count and event count) with recursive secret redaction; task and message content are not exposed. Acceptance requires deterministic protocol fixtures, bounded event sizes, authenticated administrative actions and recovery-visible state transitions.

- 2026-08-25: committed workload/memory-quality evidence is projected read-only onto the authenticated operator snapshot through fail-closed `noesis.evidence-projection.v1` digests (status `local_verified`; adds no execution capability).

### Track B — Governed self-learning

Bind terminal task outcomes to provenance receipts, deterministic holdouts, review-only proposals, explicit human approval, immutable promotion, post-promotion verification and rollback. Add evaluator registration, durable manifest tracking and `noesis.evaluator-readiness.v1`: a persisted manifest is not runtime availability after restart until the callable evaluator is explicitly re-registered with the matching digest. The completed review surface exposes bounded `noesis.learning-review-snapshot.v1` metadata through authenticated read-only `/api/learning/review`; it reports proposal/evaluator IDs, states and digests without skill or payload content. Every proposal has a provenance digest binding receipt facts, evaluation facts, skill name and content digest; approval and promotion reject stale or tampered provenance. Executable activation remains disabled by default and is never triggered by capture, evaluation, proposal, review or evaluator registration. Automatic activation without approval remains a permanent negative test.

- 2026-08-25: Gate 3 `ExecutionRecoveryExecutor` governance is locally verified — recovery mutation requires authenticated operator context, signed receipt/run identity, approved patch, fresh-base format gate and injected handler confirmation of the actual mutation, with tamper-evident rollback chains binding a durable completion receipt (status `local_verified`; executable activation remains disabled).

### Track C — Memory and long context

Extend real durable trajectories beyond fixtures: multi-session reuse, temporal decay, conflict resolution, compaction retention, attribution leakage, hard budgets and experience reuse. The durable adapter now aggregates session-qualified cases through `MultiSessionMemoryQualityReport`, and the v3 evidence runner records a real three-session, six-case distribution with cross-session reuse, decay-floor checks and reopen equality. Remaining work is broader independent corpora and repeated non-fixture distributions; report gains only with pinned corpus, fixed budgets and reproducible source IDs.

- 2026-08-25: independent adversarial memory-quality corpora v2 (12 pinned cases) and v3 (16 generated cases) are wired additively into the evidence generator with regenerated byte-stable committed evidence (status `local_verified`; deterministic self-generated distributions, not an external benchmark).

### Track D — Isolation and adversarial reliability

Unify Bubblewrap, Windows and macOS sandbox interfaces under one conformance contract. `run_conformance()` now performs command-level policy checks plus a bounded workspace-write/process-exit probe only when the selected backend is available; an unavailable host remains `not_run`, and a command-only backend cannot be reported as passed. Expand filesystem, network, credential, symlink, environment-poisoning, timeout, process-tree, cross-agent leakage, corrupted receipt, interrupted write, rollback and stale-base tests. Current Linux evidence is Bubblewrap-local; every unsupported host must return `not_run`, `blocked` or `unavailable`, never `passed`.

- 2026-08-25: the durable commit-marker ledger is bound into `MultiAgentWorkProductLoop.commit/resume`; markers are typed and idempotent, ledger conflicts fail closed before task transition, and resume exposes a marker projection (status `local_verified`).
- 2026-08-25: protocol-leakage suite v1 reaches six deterministic holdouts, including aggregate-digest isolation across sequential sessions and commit-marker authorization-scope conflict containment, with negative foreign-marker injection tests (status `local_verified`).
- 2026-08-25: the committed `noesis.workload-evidence.v1` artifact aggregates timestamp-free byte-stable MA-07 clean/crash-recovery runs, MA-08 seeded crash-injection distributions, MA-09 active-delegation denials and an output digest with a fail-closed recovery assertion (status `passed_local`; deterministic local replay metrics only).
- 2026-08-25: execution-conformance reports gain an additive `backend_verification` section exercising the `verify_backend_or_block` honesty contract against unconfigured/failing/unavailable stubs; any unexpected `passed` raises fail-closed (status `local_verified`; Windows/macOS backends remain `not_run`).
- 2026-08-25: the Windows sandbox scaffold is recorded as a `windows_hardening_inventory` of boundary-unverified entries so missing hardening is visible; the Windows sandbox execution claim remains `not_run`.

### Track E — Portable and native packaging

Produce reproducible Python 3.14 portable layouts, static manifests, SBOMs, checksums and operator bundles. The source-portable audit now builds and verifies a 415-file ZIP with SPDX-2.3 inventory and SHA-256 coverage while excluding local runtime/build outputs, models, secrets, keys and archive directories. A traversal-resistant verifier rejects unsafe manifest paths and digest/coverage mismatches. Execute the same parity contract on matching Windows and macOS hosts. Native evidence requires actual host execution, environment digest, artifact validation and clean replay; static manifests alone remain preparation evidence.

- 2026-08-25: a canonical committed-evidence registry binds the workload-evidence (recomputed digest) and release-audit (structural) artifacts into an auditable chain with a fail-closed verifier; transfer audit treats them as optional members and drifted copies are blocked (status `local_verified`). Native parity statuses are unchanged.

### Track F — External comparative lanes

Acquire exact immutable revisions and executable environments for Hermes, OpenCode and DeepSeek Harness. Use disposable workspaces, identical task manifests, fixed model/provider and budgets, deny-by-default network, credential isolation, signed result receipts, signed single-use approval receipts and independent scoring. Compare correctness, patch quality, recovery, leakage, approval bypass, latency, reviewer time and resource use. Missing lanes remain `not_run` or `blocked`.

## 3. Integration gates

| Gate | Exit condition |
|---|---|
| G-01 Baseline integrity | Claims matrix, test count, evidence inventory and clean-tree digest agree |
| G-02 Local OS integration | Tracks A–D pass their contracts on Python 3.14 with zero `ResourceWarning` violations |
| G-03 Learning governance | Track B passes proposal/approval/promotion/rollback holdouts with no automatic activation |
| G-04 Memory quality | Track C passes non-fixture trajectories, restart checks, leakage checks and hard-budget distributions |
| G-05 Isolation conformance | Track D passes Linux and has explicit native `not_run`/`blocked` evidence where hosts are absent |
| G-06 Native parity | Matching Windows/macOS runs produce validated environment, parity, SBOM and SHA-256 artifacts |
| G-07 External A/B | At least two comparable lanes pass identical protocol, revision, environment and receipt checks |
| G-08 Claim review | Independent scoring, repeated runs, security/license/provenance audits and documentation review pass |

## 4. Parallel-agent operating rules

Independent tracks may modify only their assigned files and must produce tests plus a machine-readable result. No track may silently overwrite another track’s evidence. Integration occurs only after diff review, full Python 3.14 validation, documentation/link/security audits and a clean Git tree. External or native lanes require explicit operator approval and matching environments; local simulation cannot be promoted to external success.

## 5. Honest percentage interpretation

The project may report approximately **65–70% toward a production-ready leading agent OS**, because the local governed kernel and reliability surfaces are mature. It may report only approximately **25–35% toward a proven worldwide-leading claim**, because native Windows/macOS execution and pinned external A/B evidence are still absent. The percentage reaches 100% only when the external claim package, not merely the codebase, passes the final review gate.

- 2026-08-25: the 2026-08-25 landings (commit-marker binding, protocol-leakage holdouts v1, memory corpora v2/v3 wiring, workload-evidence artifact, recovery-executor governance, Windows scaffold inventory, evidence projection, committed-evidence registry and conformance backend-verification gate) deepen already-verified local surfaces without opening any native or external lane; the conservative weighted bands therefore stay **65–70%** local-OS and **25–35%** proven-claim.

## 6. Current next actions

The immediate sequence is: freeze the claims/evidence baseline; execute Tracks A–D locally in independent work units; prepare Track E bundles for matching hosts; obtain exact pinned environments for Track F; integrate only signed evidence; then perform the final claim review. Until matching hosts and external executables are available, their statuses remain explicitly `not_run` or `blocked`.

## References

[1]: https://github.com/cloudflare/cloudflare-os "Cloudflare OS"
[2]: https://github.com/NousResearch/hermes-agent "Hermes Agent"
[3]: https://github.com/opencode-ai/opencode "OpenCode"
[4]: https://github.com/deepseek-ai/DeepSeek-V3 "DeepSeek public model reference"
[5]: https://arxiv.org/abs/2608.13417 "arXiv:2608.13417"

The upstream projects and paper are design references and benchmark targets, not evidence that NOESIS has executed or surpassed them.

## 7. Autonomous Agent OS acceptance criteria

The original target remains a complete local-first Agent OS for independent bounded work, followed by a defensible comparative claim. Local Agent OS completion requires reproducible evidence for durable checkpoint after every turn, restart-visible recovery without duplicate side effects, capability-scoped delegation with artifact isolation, human-governed learning promotion with immutable versions, fail-closed child execution, credential and network boundaries, deterministic benchmark replay, zero `ResourceWarning`, and a persistent Windows worker that records heartbeat, bounded cycle outcome, and handoff state.

The claim that NOESIS is better than Cloudflare OS or other leading agent systems is a separate evidence gate. It requires identical task manifests, pinned revisions, fixed model/provider and budgets, independent scoring, signed result receipts, and no regression in safety, provenance, recovery, or human control. Local fixtures and synthetic holdouts can validate NOESIS behavior, but cannot prove external superiority.

The execution order is: (1) finish local autonomous-loop and recovery contracts; (2) repeat adversarial local holdouts and durable-memory trajectories; (3) verify the portable Track E release; (4) prepare native packaging evidence; (5) prepare the connector-neutral Track F runner and evidence importer; and (6) perform comparative claim review only after matching external executables and pinned environments are available. Missing native or external environments remain `not_run` or `blocked`.
