# Pinned External Lane Operator Preflight

`build_operator_preflight()` проверяет prerequisites для Hermes, OpenCode и DeepSeek Harness без запуска provider и без выполнения executable. Результат имеет schema `noesis.external-lane-preflight.v1`.

Lane получает `ready` только при наличии exact revision и declared pinned executable path. Global readiness дополнительно требует workspace, deny-by-default network, отсутствие credentials и disposable workspace policy. Missing или unsafe prerequisites дают `not_run` с bounded check names.

| Поле | Обязательное значение |
|---|---|
| `execution_allowed` | `false` |
| `automatic_execution` | `false` |
| `operator_approval_required` | `true` |
| `external_execution_claim` | `false` |

`ready_for_operator_approval` означает только успешный static preflight. Это не означает, что lane запускался, создал receipt или получил score. Реальный запуск остаётся отдельной operator-approved pinned-runner операцией.
