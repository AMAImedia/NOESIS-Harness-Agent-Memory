# Projection lifecycle report export

## Назначение

HealthServer показывает lifecycle report export как bounded read-only metadata для operator dashboard, snapshot, telemetry и SSE consumers. Projection наблюдает state и не может запустить, утвердить, повторить или отменить export.

| State | Значение | Automatic control |
|---|---|---|
| `available` | Export action handler доступен, но completed receipt ещё не показывается. | `false` |
| `approved` | Зарезервировано для explicit operator-approved state при появлении asynchronous executor. | `false` |
| `exporting` | Зарезервировано для активного operator-triggered export. | `false` |
| `completed` | Signed report export receipt доступен. | `false` |
| `blocked` | Lifecycle provider завершился ошибкой или вернул invalid data. | `false` |

Projection содержит только bounded action/session/output/bundle identifiers. Signing keys, operator tokens и full receipts не раскрываются. Provider принудительно устанавливает `automatic_export=false` и `control=read_only`, даже если upstream provider передаёт конфликтующие значения.

Текущий synchronous executor показывает `available` до первого export и `completed` после добавления signed receipt. `approved` и `exporting` остаются зарезервированными состояниями, а не claims о существовании asynchronous operation.
