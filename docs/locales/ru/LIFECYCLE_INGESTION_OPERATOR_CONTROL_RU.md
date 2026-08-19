# Operator control lifecycle audit ingestion

## Назначение

HealthServer показывает lifecycle audit ingestion status как bounded metadata и предоставляет authenticated control path `POST /api/lifecycle-audit-ingestion`. Endpoint принимает только actions `preflight`, `approve` и `import`, когда у operator есть scope `lifecycle:audit:write`.

Action handler является operator-controlled и должен быть явно подключён к `LifecycleAuditIngestionAdapter`. GET snapshot/readiness/telemetry surfaces не могут запускать ingestion. HTTP projection принудительно устанавливает `automatic_import=false`, `execution_allowed=false`, `claim=false` и `control=operator_approval_required`, даже если upstream handler возвращает конфликтующие значения.

| Action | Требование | Граница |
|---|---|---|
| `preflight` | Authenticated operator и `lifecycle:audit:write`. | Записывает evidence как `awaiting_approval`; import не выполняется. |
| `approve` | Existing preflight record и explicit operator action. | Создаёт expiring approval; import не выполняется. |
| `import` | Valid non-expired approval и matching digests. | Записывает `accepted_audit_only`; execution claim не создаётся. |

Endpoint не является external-lane runner. Он не запускает providers, child processes, native builds или comparative tasks.
