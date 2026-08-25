# Memory Quality Corpora v2

Normative contract for the pinned adversarial memory-quality corpus (Gate 5, broader independent corpora) in [`noesis_harness/memory_quality_corpora.py`](../noesis_harness/memory_quality_corpora.py). This document describes the module contract; runner wiring is tracked separately (see Wiring status).

## Purpose

A deterministic, stdlib-only fixture corpus that widens memory-quality coverage without touching the core evaluator ([`noesis_harness/memory_quality.py`](../noesis_harness/memory_quality.py)). The corpus is pure constants: no wall clock, no randomness; the report digest is byte-stable across runs and machines.

## Corpus composition

`ADVERSARIAL_CORPUS_V2` pins 12 cases across 8 categories over two sessions (`v2-session-alpha`, `v2-session-beta`) with a hard budget of 64 tokens:

| Category | Cases | What it pins |
|---|---|---|
| `temporal_inversion_pair` | `v2-temporal-inversion-early`, `v2-temporal-inversion-late` | Correct ordering scores 1.0; the inverted-late case must score `temporal_order = 0.0` while recall stays 1.0. |
| `duplicate_attribution` | `v2-duplicate-attribution` | A duplicated attribution id must not inflate precision: honest precision 0.5; an inflation flag fires if the evaluator reports 1.0 anyway. |
| `near_duplicate_query` | `v2-near-duplicate-query-primary`, `-variant` | Both near-duplicate variants retain recall 1.0 and attribution precision 1.0 individually. |
| `budget_edge_long_trace` | `v2-budget-edge-exact`, `v2-budget-edge-overrun` | `used == budget` respects the hard cap; `used == budget + 1` is flagged `budget_respected = False` — detected, never silently passed. |
| `conflict_with_provenance` | `v2-conflict-provenance` | A modeled wrong conflict resolution (`conflict_resolution = 0.0`) still keeps per-case provenance verifiable. |
| `decay_floor_boundary` | `v2-decay-floor-boundary` | An at-floor record survives exactly on the floor; a sub-floor raw decay is evicted from retention though still required; retention 0.5. |
| `leakage_decoy` | `v2-leakage-decoy` | A cross-scope leak decoy scores `leakage_free = False` with attribution precision intact at 1.0. |
| `cross_session_decoy_reuse` | `v2-cross-session-decoy-alpha`, `-beta` | Real experience reuse recalls 1.0; a decoy experience reuse scores recall 0.0. |

Every case carries an entry in `EXPECTED_V2`; `evaluate_corpus_v2` lists any mismatch as `expectation_violations`.

## Module contract

- `AdversarialCorpusCaseV2` is a frozen dataclass with `payload()` (canonical JSON dict), `provenance_digest()` (`sha256:` over canonical payload), and projections `to_memory_quality_case()` / `to_trajectory_step()` into core evaluator types.
- `build_adversarial_corpus_v2()` rebuilds the tuple and fails closed on duplicate case ids (`duplicate_corpus_case_id`).
- `project_decay_strengths(base_strengths, periods)` applies exponential decay clamped at `Memory.DECAY_FLOOR` (0.1) from [`noesis_harness/memory.py`](../noesis_harness/memory.py), mirroring the store's decay model.
- `verify_case_provenance(case)` regenerates the payload purely from evaluator-bound fields and compares digests; this gap wrapper exists because the core `MemoryQualityCase` carries no provenance binding.
- `_check_decay_boundary` validates the decay fixture arithmetic fail-closed (`decay_fixture_invalid` on shape violations).
- `evaluate_corpus_v2(adapter_factory)` records every case through the adapter per session, evaluates via `MemoryQualityEvaluator`, and returns a report containing: `schema_version` (`noesis.memory-quality-corpus.v2`), `per_case` entries (metrics plus `provenance_verified`, `decay_floor_boundary_respected`, `expectation_violations`), aggregate metrics, `duplicate_attribution_inflation_detected`, `categories`, `session_ids`, an embedded `claim_boundary` string, and a byte-stable `report_digest`.
- Adapter contract: the factory must return an object exposing callable `record_trajectory(session_id, steps)` and `evaluate_sessions(sessions)`; the reference implementation is `DurableMemoryQualityAdapter`. Violations raise `adapter_factory_invalid` / `adapter_contract_invalid`.

## Typed values and error codes

`MemoryQualityCorpusError` codes: `duplicate_corpus_case_id`, `adapter_factory_invalid`, `adapter_contract_invalid`, `decay_fixture_invalid`. Per-case booleans are closed-vocabulary fields (`provenance_verified`, `decay_floor_boundary_respected`, `budget_respected`, `leakage_free`); metric values are floats in [0, 1] except token counts.

## Wiring status

As of 2026-08-25, [`scripts/run_memory_quality_evidence.py`](../scripts/run_memory_quality_evidence.py) invokes `evaluate_corpus_v2` and emits its report additively as the top-level evidence key `adversarial_corpus_v2` (evidence schema stays `noesis.memory-quality-evidence.v3`; the corpus report keeps its own `noesis.memory-quality-corpus.v2`). The regenerated [`docs/MEMORY_QUALITY_EVIDENCE.json`](MEMORY_QUALITY_EVIDENCE.json) is byte-stable across repeated runs.

## Related tests

- [`tests/test_memory_quality_corpora_v2.py`](../tests/test_memory_quality_corpora_v2.py) — size/uniqueness/schema and category coverage, two-evaluation byte equality including digest, temporal-pair detection, honest duplicate-attribution precision, budget edge compliance, provenance/decay-floor/leakage/cross-session flags, invalid adapter factories failing closed.

## Provenance

Patterns borrowed per repo discipline: evalscope-style pinned adversarial fixtures (versioned corpus, expectation table, stable digest); agentmemory decay-floor model (strength decay clamped at a floor); deepseek-harness fail-closed expectation checks; trajectory-record format follows the agentmemory quality-trace lineage of `scripts/run_memory_quality_evidence.py`.

## Claim boundary

Evidence is local and deterministic only: pinned constants scored by the local stdlib evaluator against real durable Memory operations opened by the adapter factory. Report digests attest reproducibility of fixtures and scoring math on this machine at this pinned code state. They are not external model benchmarks, not measurements of production memory quality, and not comparisons against other agents or harnesses.
