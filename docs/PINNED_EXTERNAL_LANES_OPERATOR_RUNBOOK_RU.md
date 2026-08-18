# Pinned External Lanes и Cross-Platform Operator Bundle

## Назначение

`pinned_lane_orchestrator.py` подготавливает единый connector-neutral matrix для Hermes Agent, OpenCode и DeepSeek Harness. Он не подменяет отсутствующие executable, exact revisions или native hosts и не создаёт comparative ranking при статусе `not_run`.

## Единый operator bundle

Один и тот же parity contract запускается на Python 3.14 с platform-specific launcher:

| Host | Command | Native evidence |
|---|---|---|
| Linux | `runtime/python-3.14.7/build/bin/python3.14 scripts/run_task_execution_parity.py --output artifacts/task_execution_parity.json` | Allowed on matching Linux host |
| macOS | `python3.14 scripts/run_task_execution_parity.py --output artifacts/task_execution_parity.json` | Requires matching macOS host and native sandbox backend |
| Windows | `py -3.14 scripts\\run_task_execution_parity.py --output artifacts\\task_execution_parity.json` | Requires matching Windows host and native process/job backend |

Одинаковыми остаются schema, task sequence, approval boundary, SSE assertions, recovery assertions и evidence ingestion. Различаются только native launcher и backend implementation.

## Pinned external lanes

Каждый lane обязан иметь exact immutable revision, task-manifest SHA-256, protocol fingerprint, disposable workspace, network deny-by-default, absent credentials in the child environment и explicit operator approval. Используются следующие clean-room adapters:

| Lane | Upstream reference | Executable discovery | Current status |
|---|---|---|---|
| Hermes | `https://github.com/NousResearch/hermes-agent` | `hermes` или `hermes-agent` | `not_run`, exact revision missing |
| OpenCode | `https://github.com/anomalyco/opencode` | `opencode` | `not_run`, exact revision missing |
| DeepSeek Harness | `https://github.com/deepseek-ai/deepseek-harness` | `dsh` или `deepseek-harness` | `not_run`, exact revision missing |

Запуск внешнего lane возможен только через существующий approval-gated runner. Отсутствие exact revision, executable, matching environment или signed receipt переводит lane в `not_run`/`blocked`, а не в `passed` и не в нулевую ошибку.

## Проверка

```bash
export PYTHONPATH="$PWD"
PY314=$PWD/runtime/python-3.14.7/build/bin/python3.14
$PY314 scripts/pinned_lane_orchestrator.py \
  --manifest benchmarks/external_ab_manifest_v1.json \
  --workspace /path/to/disposable-workspace \
  --output artifacts/pinned_lane_matrix.json
```

Затем оператор должен проверить exact revisions и environment digest, получить явное approval и только после этого вызвать отдельный lane runner. Matrix evidence `docs/PINNED_EXTERNAL_LANE_MATRIX_EVIDENCE.json` фиксирует текущий Linux host: все три external lanes `not_run`, ranking `not_run`, а macOS/Windows native execution ожидают соответствующие hosts.

> Этот runbook подготавливает измеримый запуск, но не выдаёт подготовку за фактический внешний A/B benchmark.
