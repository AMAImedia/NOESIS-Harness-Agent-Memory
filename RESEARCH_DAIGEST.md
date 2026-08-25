# RESEARCH_DAIGEST

Provenance digest for ported research patterns, per `AGENTS.md` discipline. Each entry names the source systems a landed pattern borrows from and the normative contract document that records the borrowing. Append-only.

## 2026-08-25 — CommitMarkerLedger

- Module: [`noesis_harness/work_product_benchmark.py`](noesis_harness/work_product_benchmark.py) (`WorkProductCommitMarkerLedger`, `WorkProductCommitMarker`), bound into `MultiAgentWorkProductLoop.commit()` / `resume()` in [`noesis_harness/multi_agent_workflow.py`](noesis_harness/multi_agent_workflow.py).
- Source patterns: LoopX append-only, fingerprint-idempotent event-sourced state via [`noesis_harness/event_store.py`](noesis_harness/event_store.py); agentmemory governance conflict handling — an identical double-send is absorbed as a replay, identity or content divergence is denied fail-closed and never rewritten.
- Contract doc: [`docs/WORK_PRODUCT_COMMIT_MARKERS.md`](docs/WORK_PRODUCT_COMMIT_MARKERS.md) (RU: [`docs/locales/ru/WORK_PRODUCT_COMMIT_MARKERS_RU.md`](docs/locales/ru/WORK_PRODUCT_COMMIT_MARKERS_RU.md)).
- Tests: [`tests/test_work_product_gate4_gap.py`](tests/test_work_product_gate4_gap.py), [`tests/test_multi_agent_workflow_markers.py`](tests/test_multi_agent_workflow_markers.py).

## 2026-08-25 — ProtocolLeakageSuite

- Module: [`noesis_harness/protocol_leakage_holdouts.py`](noesis_harness/protocol_leakage_holdouts.py).
- Source patterns: Hermes/OpenCode observability redaction norms — minimal typed event envelopes crossing the sink boundary, secret-free audit trails; deepseek-harness fail-closed evidence handling — any unexpected exception classifies a holdout as failed, never passed; fixed-corpus negative/positive holdout discipline of [`noesis_harness/isolation_holdouts.py`](noesis_harness/isolation_holdouts.py) (agentmemory-lineage deterministic leakage cases).
- Contract doc: [`docs/PROTOCOL_LEAKAGE_HOLDOUTS.md`](docs/PROTOCOL_LEAKAGE_HOLDOUTS.md) (RU: [`docs/locales/ru/PROTOCOL_LEAKAGE_HOLDOUTS_RU.md`](docs/locales/ru/PROTOCOL_LEAKAGE_HOLDOUTS_RU.md)).
- Tests: [`tests/test_protocol_leakage_holdouts.py`](tests/test_protocol_leakage_holdouts.py).

## 2026-08-25 — Memory quality corpora v2

- Module: [`noesis_harness/memory_quality_corpora.py`](noesis_harness/memory_quality_corpora.py) (pinned adversarial fixture corpus, Gate 5 broader independent corpora).
- Source patterns: evalscope-style pinned adversarial fixtures — versioned corpus with a closed expectation table and byte-stable report digest; agentmemory decay-floor model — exponential strength decay clamped at `Memory.DECAY_FLOOR`; deepseek-harness fail-closed expectation checks; trajectory-record format follows the agentmemory quality-trace lineage of [`scripts/run_memory_quality_evidence.py`](scripts/run_memory_quality_evidence.py).
- Contract doc: [`docs/MEMORY_QUALITY_CORPUS_V2.md`](docs/MEMORY_QUALITY_CORPUS_V2.md) (RU: [`docs/locales/ru/MEMORY_QUALITY_CORPUS_V2_RU.md`](docs/locales/ru/MEMORY_QUALITY_CORPUS_V2_RU.md)).
- Tests: [`tests/test_memory_quality_corpora_v2.py`](tests/test_memory_quality_corpora_v2.py).

## 2026-08-25 — Learning corpus binding (Gate 1 evidence provenance)

- Module: [`noesis_harness/learning_corpus_binding.py`](noesis_harness/learning_corpus_binding.py), integrated additively into `PromotionIntegration.propose` in [`noesis_harness/promotion_integration.py`](noesis_harness/promotion_integration.py) (optional keyword-only `corpus_binding`).
- Source patterns: agentmemory governance audit lineage — tamper-evident canonical-JSON + sha256 integrity envelope with fail-closed verification (`hmac.compare_digest`) as already ported in learning_promotion/promotion_integration; deepseek-harness adversarial fail-closed discipline mirrored in `memory_quality_corpora.verify_case_provenance`. Deterministic-core rule preserved: no wall clock unless a caller injects one; default bindings are byte-stable.
- Contract doc: none yet; behavior documented in the module docstring and enforced by tests (telemetry key `corpus_binding`, schema `noesis.learning-corpus-binding.v1`).
- Tests: [`tests/test_learning_corpus_binding.py`](tests/test_learning_corpus_binding.py).

## 2026-08-25 — Learning corpus binding contract doc

- Module: [`noesis_harness/learning_corpus_binding.py`](noesis_harness/learning_corpus_binding.py), integrated keyword-only into `PromotionIntegration.propose` in [`noesis_harness/promotion_integration.py`](noesis_harness/promotion_integration.py).
- Source patterns: agentmemory governance receipt patterns — tamper-evident canonical JSON + sha256 integrity envelope with fail-closed verification; deepseek-harness fail-closed verification discipline.
- Contract doc: [`docs/LEARNING_CORPUS_BINDING.md`](docs/LEARNING_CORPUS_BINDING.md) (RU: [`docs/locales/ru/LEARNING_CORPUS_BINDING_RU.md`](docs/locales/ru/LEARNING_CORPUS_BINDING_RU.md)). Supersedes the "none yet" note in the entry above; recorded append-only.
- Tests: [`tests/test_learning_corpus_binding.py`](tests/test_learning_corpus_binding.py).

## 2026-08-25 — Multi-agent workload evidence generator

- Module: [`scripts/run_workload_evidence.py`](scripts/run_workload_evidence.py) (Gate 4 deterministic local evidence; schema `noesis.workload-evidence.v1`; artifact path `docs/MULTI_AGENT_WORKLOAD_EVIDENCE.json` via `--output`).
- Source patterns: deepseek-harness deterministic rubric workloads (bounded no-hidden-reward scoring via [`noesis_harness/work_product_benchmark.py`](noesis_harness/work_product_benchmark.py)) + LoopX idempotent append-only aggregation ([`noesis_harness/work_product_ma07.py`](noesis_harness/work_product_ma07.py)).
- Contract doc: [`docs/MULTI_AGENT_WORKLOAD_EVIDENCE.md`](docs/MULTI_AGENT_WORKLOAD_EVIDENCE.md) (RU: [`docs/locales/ru/MULTI_AGENT_WORKLOAD_EVIDENCE_RU.md`](docs/locales/ru/MULTI_AGENT_WORKLOAD_EVIDENCE_RU.md)).
- Tests: [`tests/test_workload_evidence.py`](tests/test_workload_evidence.py).

## 2026-08-25 — Memory quality corpora v3

- Module: [`noesis_harness/memory_quality_corpora_v3.py`](noesis_harness/memory_quality_corpora_v3.py) (Gate 1 broader independent corpora, seeded generated adversarial fixtures), wired into [`scripts/run_memory_quality_evidence.py`](scripts/run_memory_quality_evidence.py) as evidence key `adversarial_corpus_v3`.
- Source patterns: evalscope seeded-fixture generation (explicit LCG over finite tables, seed-sensitivity probes, stable digests) + agentmemory decay-floor model (strength decay clamped at `Memory.DECAY_FLOOR`); LCG stream ported from [`noesis_harness/work_product_ma08_ma09.py`](noesis_harness/work_product_ma08_ma09.py).
- Contract doc: [`docs/MEMORY_QUALITY_CORPUS_V3.md`](docs/MEMORY_QUALITY_CORPUS_V3.md) (RU: [`docs/locales/ru/MEMORY_QUALITY_CORPUS_V3_RU.md`](docs/locales/ru/MEMORY_QUALITY_CORPUS_V3_RU.md)).
- Tests: [`tests/test_memory_quality_corpora_v3.py`](tests/test_memory_quality_corpora_v3.py).

## 2026-08-25 — Evidence projection (fail-closed operator digest surface)

- Module: [`noesis_harness/evidence_projection.py`](noesis_harness/evidence_projection.py) (`project_evidence`, schema `noesis.evidence-projection.v1`), integrated keyword-only into `HealthServer.operator_snapshot` in [`noesis_harness/health_server.py`](noesis_harness/health_server.py) (optional `evidence_projection`, default unchanged).
- Source patterns: deepseek-harness fail-closed verification discipline (missing/corrupt input degrades to a typed unavailable status, never raises; `hmac.compare_digest` over canonical JSON) + LoopX read-only projections (deterministic view over committed state without mutation); canonical-JSON digest verification follows the signed report bundle / lifecycle audit ingestion lineage.
- Contract doc: [`docs/EVIDENCE_PROJECTION.md`](docs/EVIDENCE_PROJECTION.md) (RU: [`docs/locales/ru/EVIDENCE_PROJECTION_RU.md`](docs/locales/ru/EVIDENCE_PROJECTION_RU.md)).
- Tests: [`tests/test_evidence_projection.py`](tests/test_evidence_projection.py).
