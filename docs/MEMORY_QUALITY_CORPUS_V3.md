# Memory Quality Corpora v3

Normative contract for the Gate 1 broader independent corpora family in [`noesis_harness/memory_quality_corpora_v3.py`](../noesis_harness/memory_quality_corpora_v3.py): the second adversarial memory-quality corpus, produced by an independent seeded procedure rather than hand-pinned constants.

## Purpose

A deterministic, stdlib-only fixture corpus generated from an explicit linear congruential generator over small finite tables. Identical seeds reproduce byte-identical corpora while different seeds structurally differ; both properties are asserted fail-closed inside the generator. The untouched core evaluator ([`noesis_harness/memory_quality.py`](../noesis_harness/memory_quality.py)) remains the only scorer: no wall clock, no `random` module.

## Corpus composition

`generate_corpus_v3(seed=8675309, cases_per_category=2)` emits 8 categories x `cases_per_category` cases (1..16 per category) across two sessions named `v3-c<seed>-session-alpha` and `v3-c<seed>-session-beta`, with a per-corpus budget drawn in [48, 80]:

| Category | Generated shape | What it pins |
|---|---|---|
| `temporal_inversion_pair` | Alternating correct/inverted ordering | Correct ordering scores 1.0; inverted members must score `temporal_order = 0.0` at recall 1.0. |
| `duplicate_attribution` | Duplicated attribution (2-3 copies) plus 1-2 noise sources | Honest attribution precision below 1.0; an inflation flag fires if the evaluator reports 1.0 anyway. |
| `near_duplicate_query` | Own source plus a variant source with distinct hex tokens | Recall 1.0 and attribution precision 1.0 individually against near-duplicate selections. |
| `budget_edge_long_trace` | Long traces of 6-10 ids; overruns on odd indices | `used == budget` respects the hard cap; `used == budget + 1` is flagged `budget_respected = False`. |
| `conflict_with_provenance` | Current vs stale source; wrong resolution on even indices | A modeled wrong conflict resolution still keeps per-case provenance verifiable. |
| `decay_floor_boundary` | At-floor and sub-floor base strengths, periods 1-2, multipliers 0.5/0.75 | At-floor record survives exactly on the floor; sub-floor raw decay is evicted though required; retention 0.5. |
| `leakage_decoy` | Cross-scope decoy on even indices | Decoy members score `leakage_free = False` with attribution precision intact. |
| `cross_session_decoy_reuse` | Session-beta reuse of real vs decoy experience | Real experience reuse recalls 1.0; decoy reuse scores experience-reuse recall 0.0. |

The expectation table is rebuilt arithmetically from generator metadata on every evaluation (`expected_metrics_v3`), so generator and evaluator must agree independently.

## Module contract

- `AdversarialCorpusCaseV3` is a frozen dataclass with `payload()` (canonical JSON dict), `provenance_digest()` (`sha256:` over canonical payload), and projections `to_memory_quality_case()` / `to_trajectory_step()` into core evaluator types.
- `_LcgRandom` ports the 32-bit LCG stream from `work_product_ma08_ma09` (high-bit draws avoid short cycles); identifier minting guarantees uniqueness with bounded retries (`source_id_space_exhausted`, `lcg_draw_space_exhausted`, `lcg_bound_invalid` on malformed bounds).
- `generate_corpus_v3(seed, cases_per_category)` validates parameters fail-closed and runs internal probes before returning: unique case ids (`duplicate_corpus_case_id`), exact size (`corpus_size_invalid`), exact category set (`corpus_category_set_invalid`), same-seed replay equality (`same_seed_divergence_detected`), cross-seed digest inequality (`cross_seed_collision_detected`), and cross-seed id disjointness (`cross_seed_id_collision_detected`). A broken property aborts generation instead of emitting an unverifiable corpus.
- `project_decay_strengths_v3(base_strengths, periods)` applies exponential decay clamped at `Memory.DECAY_FLOOR` (0.1) from [`noesis_harness/memory.py`](../noesis_harness/memory.py), mirroring the store's decay model.
- `verify_case_provenance_v3(case)` rebuilds the payload purely from evaluator-bound fields via the trajectory round-trip and compares digests.
- `_check_decay_boundary_v3(case)` validates the decay fixture arithmetic fail-closed (`decay_fixture_invalid`).
- `evaluate_corpus_v3(adapter_factory, seed, cases_per_category)` records every case through the adapter per session, evaluates via `MemoryQualityEvaluator`, and returns a report containing: `schema_version` (`noesis.memory-quality-corpus.v3`), `per_case` entries (metrics plus `provenance_verified`, `decay_floor_boundary_respected`, `expectation_violations`), aggregate metrics, `duplicate_attribution_inflation_detected`, `categories`, `corpus_digest`, `seed`, `session_ids`, an embedded `claim_boundary` string, and a byte-stable `report_digest`.
- Adapter contract: the factory must be callable and return an object exposing callable `record_trajectory(session_id, steps)` and `evaluate_sessions(sessions)`; violations raise `adapter_factory_invalid` / `adapter_contract_invalid`; unknown or missing expectation entries raise `expectation_key_unknown` / `expectation_entry_missing`.

## Typed values and error codes

`MemoryQualityCorpusError` codes: `seed_invalid`, `cases_per_category_invalid`, `cases_per_category_out_of_range`, `lcg_bound_invalid`, `lcg_draw_space_exhausted`, `source_id_space_exhausted`, `duplicate_corpus_case_id`, `corpus_size_invalid`, `corpus_category_set_invalid`, `same_seed_divergence_detected`, `cross_seed_collision_detected`, `cross_seed_id_collision_detected`, `category_unknown`, `expectation_entry_missing`, `expectation_key_unknown`, `adapter_factory_invalid`, `adapter_contract_invalid`, `decay_fixture_invalid`.

Per-case booleans are closed-vocabulary fields (`provenance_verified`, `decay_floor_boundary_respected`, `budget_respected`, `leakage_free`); metric values are floats in [0, 1] except token counts and the integer `seed`.

## Wiring status

As of 2026-08-25, [`scripts/run_memory_quality_evidence.py`](../scripts/run_memory_quality_evidence.py) invokes `evaluate_corpus_v3` through `run_adversarial_corpus_v3()` and emits its report additively as the top-level evidence key `adversarial_corpus_v3` (evidence schema stays `noesis.memory-quality-evidence.v3`; the corpus report keeps its own `noesis.memory-quality-corpus.v3`). The regenerated [`docs/MEMORY_QUALITY_EVIDENCE.json`](MEMORY_QUALITY_EVIDENCE.json) is byte-stable across repeated runs.

## Related tests

- [`tests/test_memory_quality_corpora_v3.py`](../tests/test_memory_quality_corpora_v3.py) — same-seed byte equality including digests, cross-seed id/content divergence, size/category/id coverage, expectation-table completeness, parameter validation fail-closed, temporal inversion detected dynamically by category, decay/leakage/budget/reuse edges failing visibly or not at all, custom `cases_per_category` determinism, and adapter contract violations failing closed.

## Provenance

Patterns borrowed per repo discipline: evalscope seeded-fixture generation (explicit seeded procedure over finite tables, versioned schema, stable digests, seed-sensitivity probes); agentmemory decay-floor model (strength decay clamped at a floor); LCG stream ported from `work_product_ma08_ma09`; fail-closed expectation checks in the spirit of deepseek-harness adversarial suites; recorded-trajectory scoring follows the agentmemory quality-trace lineage of `scripts/run_memory_quality_evidence.py`.

## Claim boundary

Evidence is local and deterministic only: seeded generated constants scored by the local stdlib evaluator against real durable Memory operations opened by the adapter factory. Report and corpus digests attest reproducibility of generation and scoring math on this machine at this pinned code state. They are not external model benchmarks, not measurements of production memory quality, and not comparisons against other agents or harnesses.
