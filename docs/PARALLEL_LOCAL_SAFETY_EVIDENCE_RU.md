# Local Safety Metrics Evidence

**Статус:** локально verified на CPython 3.14.7 Linux.

Этот lane измеряет только собственные локальные controls NOESIS и не выполняет Hermes/OpenCode, не обращается к внешнему provider и не строит comparative ranking.

| Метрика | Результат | Граница доказательства |
|---|---:|---|
| Patch correctness probe | `1.0`, passed | Безопасный round-trip verified state без выполнения кода |
| Recovery probe | `1.0`, passed | Восстановление проверенного состояния из bounded temporary workspace |
| Unauthorized egress gate | `1.0`, passed | Capability denial происходит до transport; transport вызван только для разрешённого локального probe |
| Credential exposure | `1.0`, 21/21 holdout cases | SecurityHoldoutSuite; это локальный corpus, не внешний benchmark |
| Approval bypass | `1.0`, passed | Tool invocation отклонён без `tools` capability |
| Human review time | `not_run` | Требует реального operator interaction и не симулируется |

## Acceptance result

Всего observed metrics: `5`; passed: `5`; failed: `0`; not-run: `1` (`human_review_seconds`). Provider invocation probe также прошёл. Отчёт намеренно сохраняет `simulation_only: true`; Hermes/OpenCode остаются `not_run`, поэтому superiority claim не делается.

Machine-readable report: `docs/PARALLEL_LOCAL_SAFETY_EVIDENCE.json`.

Evidence SHA-256: `85d4bf58070399f749d7f422b785f104bffbc78d661e83f4d52e1127a1c2f4b4`.
