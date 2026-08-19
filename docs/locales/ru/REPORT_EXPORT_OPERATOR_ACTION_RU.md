# Authenticated operator report export action

## Назначение

`POST /api/report-export` — operator-owned control path для экспорта bounded HealthServer snapshot в signed report bundle. GET snapshot, readiness, telemetry и SSE surfaces остаются read-only.

Action использует `noesis.report-export-action.v1`, требует scope `report:export`, связывает operator/session, output filename и exact snapshot digest и подписывается HMAC-SHA256. Executor сохраняет одноразовый audit record `noesis.report-export-receipt.v1`.

| Guard | Поведение при нарушении |
|---|---|
| Нет operator context или handler | `403`/`405`; export не выполняется. |
| Неверный operator или отсутствует scope | Отклонение до snapshot/export. |
| Signature или schema failure | Отклонение до export. |
| Snapshot digest drift | Отклонение до записи bundle. |
| Path traversal или не-ZIP output name | Отклонение до записи. |
| Replayed action ID | Отклонение; второй bundle/receipt не создаётся. |
| Provider exception | Успешный receipt не создаётся. |

Handler вызывает только offline snapshot exporter. Он не запускает external lanes, providers, child processes или native builds. Signed bundle остаётся export artifact с `claim=false`; это не approval, execution receipt и не comparative score.
