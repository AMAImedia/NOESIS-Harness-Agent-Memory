# Ingestion lifecycle audit bundle

## Назначение

`LifecycleAuditIngestionAdapter` импортирует verified report bundle и его signed lifecycle JSONL audit log в durable SQLite ledger. Это audit-only import path. Он не запускает providers, child runtimes, native builds или external lanes.

| Stage | Поведение |
|---|---|
| `preflight` | Проверяет deterministic report bundle, все lifecycle signatures/order, stale files и duplicate bundle digests; затем записывает `awaiting_approval`. |
| `approved` | Записывает explicit operator approval, связанный с bundle digest, audit digest, operator identity и expiry. |
| `imported` | После проверки approval записывает `accepted_audit_only`. |
| `blocked` | Используется для malformed/tampered/stale/duplicate evidence или недоступной verification. |
| `rejected` | Используется для invalid, expired или identity-mismatched approval. |

Adapter использует отдельную schema `noesis.lifecycle-audit-ingestion.v1` и durable append-only SQLite events. Каждый result принудительно устанавливает `execution_allowed=false`, `automatic_execution=false` и `claim=false`. Imported lifecycle audit не может закрыть `delegated` или `child_runtime` lanes и не может повысить native, external, comparative или worldwide claims.
