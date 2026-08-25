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
