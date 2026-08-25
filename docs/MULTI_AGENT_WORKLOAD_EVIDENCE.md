# Multi-Agent Workload Evidence

Normative contract for the Gate 4 deterministic local workload-evidence generator [`scripts/run_workload_evidence.py`](../scripts/run_workload_evidence.py). It composes existing harness modules into one byte-stable machine-readable JSON artifact; runner wiring is tracked separately (see Wiring status).

## Purpose

One artifact that evidences bounded multi-lane workload replay with injected first-attempt crashes, crash-injection probes, simultaneous active-delegation isolation, and a bounded no-hidden-reward rubric evaluation. The output contains no wall-clock value of any kind: `generated_at` is omitted entirely and every quantity derives from fixed seeds, fixed fixtures, or the deterministic cost model. Only the final `output_digest` depends on the rest of the document, so identical inputs reproduce identical bytes.

## Evidence composition

Schema `noesis.workload-evidence.v1`; top-level keys:

| Key | What it pins |
|---|---|
| `ma07_workload` | Two real 3-lane `WorkProductWorkloadRunner` runs (max concurrency 2, retry limit 1): a clean run (all lanes pass on attempt 1) and a crash run with an injected first-attempt crash on task `crash-task-b`. A recovery assertion requires the injected task to recover in exactly 2 attempts with all statuses `passed`; otherwise the section is `blocked` with reason `injected_first_attempt_crash_not_recovered`. Each run reports its own aggregate digest; clean and crash digests must differ. |
| `ma08_crash_injection` | `CrashInjectionProber` over 5 phases (`pre_write`, `post_write`, `pre_read`, `post_read`, `workspace_escape`) with repetitions = 10 and seed = 20260825; per-phase summaries carry run counts and deterministic cost-model latency statistics (`min_ms <= p50_ms <= p95_ms <= max_ms`) plus survival rate. |
| `ma09_active_delegation` | `ActiveDelegationProber().run_simultaneous()`: 4 simultaneous active-delegation isolation probes, each expected to be denied (`observed` starts with `denied:`) and to pass its assertion; section passes only when `all_passed` is true. |
| `evaluator_metrics` | Bounded no-hidden-reward rubric: `WorkProductBenchmarkEvaluator` over 6 fixed outcomes — correctness 5/6, delivery 5/6, leakage-free 1.0, recovery 1/3, review approval 4/6, commit 5/6, retry 1/3, work-product score 27/36. |
| `claim_boundary` | Embedded constant string (see Claim boundary). |
| `output_digest` | `sha256:` over the canonical JSON of every other key. |

## Generator contract

- `build_evidence()` assembles the document and is byte-stable across invocations; `output_digest` is computed last over the canonical payload.
- MA-07 aggregation follows LoopX append-only/idempotent patterns via [`noesis_harness/work_product_ma07.py`](../noesis_harness/work_product_ma07.py); crash-injection and probe repetition follow deepseek-harness/Hermes patterns via [`noesis_harness/work_product_ma08_ma09.py`](../noesis_harness/work_product_ma08_ma09.py); rubric scoring uses [`noesis_harness/work_product_benchmark.py`](../noesis_harness/work_product_benchmark.py).
- Overall status is `passed` only when all three probe sections hold: ma07 recovery asserted, ma08 covers exactly 5 phases at 10 runs each, ma09 `all_passed`.
- CLI: `--output` is required; the script writes indented sorted-key JSON with a trailing newline and exits 0 on `passed`, 2 on `blocked`. CLI/output conventions follow the sibling generators `scripts/run_memory_quality_evidence.py` and `scripts/run_task_execution_parity.py`.

## Typed values and error codes

Statuses are the closed vocabulary `passed` / `blocked` (`STATUS_PASSED` / `STATUS_BLOCKED`). The single typed blocked reason is `injected_first_attempt_crash_not_recovered`. Exit codes: 0 for passed evidence, 2 for blocked. No exceptions are part of the output contract.

## Wiring status

The generator [`scripts/run_workload_evidence.py`](../scripts/run_workload_evidence.py) exists and writes its artifact to the path given via `--output`; the canonical artifact path for this gate is `docs/MULTI_AGENT_WORKLOAD_EVIDENCE.json`. Presence of that file is not asserted by this document: the artifact may be generated concurrently and regenerated at any pinned code state.

## Related tests

- [`tests/test_workload_evidence.py`](../tests/test_workload_evidence.py) — schema shape, MA-07 injected-crash recovery contract (clean vs crash attempts, recovered tasks, differing aggregate digests), MA-08 phase coverage and determinism inputs, MA-09 denial assertions, exact evaluator-metric fixture ratios, digest integrity and byte stability across builds, and absence of any timestamp-like key or value anywhere in the serialized document.

## Provenance

Patterns borrowed per repo discipline: deepseek-harness deterministic rubric workloads (bounded no-hidden-reward scoring via `work_product_benchmark`) and crash-injection probes; LoopX idempotent append-only aggregation via `work_product_ma07`; Hermes probe repetition and agent-teams workspace-isolation patterns via `work_product_ma08_ma09`.

## Claim boundary

Embedded claim boundary: `deterministic_local_workload_replay_crash_injection_active_delegation_and_bounded_rubric_metrics_only_no_external_model_no_network_no_wall_clock`. Evidence attests reproducibility of local replay, injection, isolation, and rubric math on this machine at this pinned code state; it is not an external model benchmark and measures no networked or wall-clock behavior.
