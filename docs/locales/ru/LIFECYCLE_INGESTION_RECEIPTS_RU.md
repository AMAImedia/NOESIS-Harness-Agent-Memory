# Receipts lifecycle ingestion

`LifecycleAuditIngestionAdapter` создаёт signed `noesis.lifecycle-audit-ingestion-receipt.v1` receipt для каждого успешного action `preflight`, `approve` и `import`. Receipt связывает `action_id`, action type, operator identity, record ID, state, bundle digest и audit digest.

Receipts append-only и хранятся вместе с durable ingestion record. Используется HMAC-SHA256; signing key никогда не попадает в receipt. Invalid approval, stale approval, duplicate import или tampered input приводят к rejection/blocked ledger state, а не к успешному receipt.

HealthServer показывает только bounded receipt metadata (`schema_version`, `action_id`, action, state и operator ID). Signatures, keys, full approval payloads и digests не выдаются через status projection. Receipt validity является только audit evidence; каждая projection сохраняет `claim=false`, `execution_allowed=false` и `automatic_import=false`.
