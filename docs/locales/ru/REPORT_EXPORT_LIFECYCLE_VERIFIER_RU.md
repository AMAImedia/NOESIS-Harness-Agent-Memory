# Verifier lifecycle evidence report export

## Назначение

`verify_lifecycle_events()` и `verify_lifecycle_file()` проверяют signed `noesis.report-export-lifecycle-event.v1` records до их использования как audit evidence. Verifier проверяет schema, required identity, HMAC signature, duplicate event IDs, grouping по session/action и lifecycle ordering.

Корректный lifecycle log получает `status=passed` только для audit verification. `lifecycle_audit_only_projection()` всегда возвращает `claim=false`, `execution_claim=false` и `comparative_claim=false`. Lifecycle events не могут закрыть signed execution lanes, требуемые comparative aggregator.

| Rejection | Результат |
|---|---|
| Invalid JSON/schema/identity | `blocked` |
| Signature tamper или wrong key | `blocked` |
| Duplicate event ID | `blocked` |
| Invalid action/session ordering | `blocked` |
| Empty input | `not_run` |
| Valid signed lifecycle log | `passed`, только audit |

Replayed action может иметь terminal `blocked` event после ранее completed sequence; второй completed receipt не создаётся, comparative claim не повышается.

`lifecycle_audit_readiness()` показывает verified result как отдельный domain `report_export_lifecycle_audit`. Он всегда возвращает `execution_lane_satisfied=false`, `native_lane_satisfied=false` и `external_lane_satisfied=false`, даже если audit log успешно проверен. HealthServer проецирует этот domain в operator snapshot, telemetry, readiness surfaces и `/api/readiness`.
