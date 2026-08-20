# Real Durable Memory Reuse Stress

This is the normative contract for the next memory-quality gate: measuring durable recall from the real SQLite-backed `Memory` store across repeated sessions and reopen boundaries. The gate is **deterministic, bounded, trace-backed, and honest about fixture versus external evidence**.

## Contract

The stress runner writes one relevant semantic fact and a bounded set of distractors for each repetition. It queries the real memory store, records selected and relevant IDs in the durable quality trace store, closes and reopens the memory database, and verifies that the relevant fact remains recallable. Each repetition uses a distinct session and deterministic query token. The aggregate report includes the recall distribution, mean, session/case counts, persistence status, and a SHA-256 distribution digest.

| Requirement | Acceptance rule |
|---|---|
| Real storage | Facts are written through `Memory.save`, not injected directly into quality records. |
| Real recall | Selection is obtained through `Memory.recall`; the evaluator does not infer hits from the expected answer. |
| Durable traces | Every case is persisted through `DurableMemoryQualityTraceStore` and reloaded for aggregation. |
| Reopen boundary | The memory database is reopened after every repetition and the relevant ID is checked again. |
| Repeated distribution | Repetitions are bounded to `1..100`; scale and token budget must be positive. |
| Determinism | Session IDs, query tokens, case IDs, and distribution digest are deterministic for a fixed run shape. |
| Fail-closed behavior | Invalid bounds and trace conflicts are rejected; missing traces cannot produce a report. |

## Boundary

This gate measures local persistence and retrieval behavior, not general intelligence, semantic coverage, or superiority over another agent. The relevant fact and distractors are deterministic stress inputs. Native Windows/macOS execution, external Hermes/OpenCode/DeepSeek Harness A/B, and model-based long-context claims remain `not_run` until matching pinned environments and signed operator-approved evidence are available.

## Implementation and evidence

The implementation is [`noesis_harness/memory_quality.py`](../noesis_harness/memory_quality.py), exposed as `run_real_memory_reuse_stress` through [`noesis_harness/__init__.py`](../noesis_harness/__init__.py). Focused coverage is in [`tests/test_memory_quality.py`](../tests/test_memory_quality.py), including reopen persistence, repeated distributions, deterministic digest comparison, invalid-bound rejection, durable aggregation, and ResourceWarning hygiene.
