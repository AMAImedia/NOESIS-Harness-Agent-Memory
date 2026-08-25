# Multi-Agent Workload Evidence — русская локализация

Это supplemental-описание English primary contract для Gate 4 детерминированного локального workload-evidence генератора [`scripts/run_workload_evidence.py`](../../../scripts/run_workload_evidence.py). Он компонует существующие harness-модули в один байт-стабильный machine-readable JSON артефакт; wiring runner'а отслеживается отдельно (см. Wiring status). English primary contract: [`MULTI_AGENT_WORKLOAD_EVIDENCE.md`](../../MULTI_AGENT_WORKLOAD_EVIDENCE.md).

## Purpose

Один артефакт, evidencing bounded multi-lane workload replay с injected first-attempt crashes, crash-injection probes, simultaneous active-delegation isolation и bounded no-hidden-reward rubric evaluation. В output нет wall-clock значений любого рода: `generated_at` опущен полностью, каждая величина выводится из фиксированных seeds, fixtures или детерминированной cost model. Только финальный `output_digest` зависит от остального документа, поэтому идентичные входы воспроизводят идентичные байты.

## Evidence composition

Schema `noesis.workload-evidence.v1`; top-level ключи:

| Ключ | Что пиннит |
|---|---|
| `ma07_workload` | Два реальных 3-lane прогона `WorkProductWorkloadRunner` (max concurrency 2, retry limit 1): clean run (все lanes проходят с попытки 1) и crash run с injected first-attempt crash на задаче `crash-task-b`. Recovery assertion требует восстановления injected задачи ровно за 2 attempts при всех статусах `passed`; иначе секция `blocked` с причиной `injected_first_attempt_crash_not_recovered`. Каждый прогон несёт свой aggregate digest; digests clean и crash обязаны различаться. |
| `ma08_crash_injection` | `CrashInjectionProber` по 5 phases (`pre_write`, `post_write`, `pre_read`, `post_read`, `workspace_escape`), repetitions = 10, seed = 20260825; per-phase summaries несут счётчики прогонов и статистики latency детерминированной cost model (`min_ms <= p50_ms <= p95_ms <= max_ms`) плюс survival rate. |
| `ma09_active_delegation` | `ActiveDelegationProber().run_simultaneous()`: 4 simultaneous active-delegation isolation probes, каждая ожидаемо denied (`observed` начинается с `denied:`) и проходит assertion; секция passes только при `all_passed`. |
| `evaluator_metrics` | Bounded no-hidden-reward rubric: `WorkProductBenchmarkEvaluator` над 6 фиксированными outcomes — correctness 5/6, delivery 5/6, leakage-free 1.0, recovery 1/3, review approval 4/6, commit 5/6, retry 1/3, work-product score 27/36. |
| `claim_boundary` | Встроенная константа (см. Claim boundary). |
| `output_digest` | `sha256:` над canonical JSON всех остальных ключей. |

## Generator contract

- `build_evidence()` собирает документ и байт-стабилен между вызовами; `output_digest` считается последним над canonical payload.
- MA-07 агрегация следует LoopX append-only/idempotent паттернам через [`noesis_harness/work_product_ma07.py`](../../../noesis_harness/work_product_ma07.py); crash-injection и probe repetition — паттерны deepseek-harness/Hermes через [`noesis_harness/work_product_ma08_ma09.py`](../../../noesis_harness/work_product_ma08_ma09.py); rubric scoring — [`noesis_harness/work_product_benchmark.py`](../../../noesis_harness/work_product_benchmark.py).
- Overall status равен `passed` только когда все три probe-секции держатся: ma07 recovery asserted, ma08 покрывает ровно 5 phases по 10 runs, ma09 `all_passed`.
- CLI: `--output` required; скрипт пишет indented sorted-key JSON с trailing newline и выходит с кодом 0 при `passed`, 2 при `blocked`. CLI/output conventions следуют sibling-генераторам `scripts/run_memory_quality_evidence.py` и `scripts/run_task_execution_parity.py`.

## Typed values and error codes

Статусы — закрытый словарь `passed` / `blocked` (`STATUS_PASSED` / `STATUS_BLOCKED`). Единственная типизированная blocked-причина — `injected_first_attempt_crash_not_recovered`. Exit codes: 0 для passed evidence, 2 для blocked. Исключения не входят в output contract.

## Wiring status

Генератор [`scripts/run_workload_evidence.py`](../../../scripts/run_workload_evidence.py) существует и пишет артефакт по пути из `--output`; канонический путь артефакта этого gate — `docs/MULTI_AGENT_WORKLOAD_EVIDENCE.json`. Наличие файла данным документом не утверждается: артефакт может генерироваться конкурентно и регенерироваться на любом pinned состоянии кода.

## Related tests

- [`tests/test_workload_evidence.py`](../../../tests/test_workload_evidence.py) — shape схемы, MA-07 контракт восстановления injected crash (attempts clean vs crash, recovered tasks, различающиеся aggregate digests), покрытие phases MA-08 и determinism inputs, denial assertions MA-09, точные ratios evaluator-metrics fixture, integrity и byte stability digest между сборками, отсутствие timestamp-подобных ключей и значений где либо в сериализованном документе.

## Provenance

Заимствованные паттерны: deterministic rubric workloads deepseek-harness (bounded no-hidden-reward scoring через `work_product_benchmark`) и crash-injection probes; LoopX idempotent append-only агрегация через `work_product_ma07`; probe repetition Hermes и workspace-isolation agent-teams через `work_product_ma08_ma09`.

## Claim boundary

Встроенный claim boundary: `deterministic_local_workload_replay_crash_injection_active_delegation_and_bounded_rubric_metrics_only_no_external_model_no_network_no_wall_clock`. Evidence подтверждает воспроизводимость локальных replay, injection, isolation и rubric math на этой машине в данном pinned состоянии кода; это не внешний model benchmark и не измерение сетевого или wall-clock поведения.
