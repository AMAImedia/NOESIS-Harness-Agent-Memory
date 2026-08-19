# Lifecycle Ingestion Action Receipts

`LifecycleAuditIngestionAdapter` emits a signed `noesis.lifecycle-audit-ingestion-receipt.v1` receipt for each successful `preflight`, `approve`, and `import` action. The receipt binds `action_id`, action type, operator identity, record ID, state, bundle digest, and audit digest.

Receipts are append-only and stored with the durable ingestion record. They use HMAC-SHA256 and never contain the signing key. Invalid approval, stale approval, duplicate import, or tampered input produces a rejection/blocked ledger state rather than a successful receipt.

HealthServer exposes only bounded receipt metadata (`schema_version`, `action_id`, action, state, and operator ID). It does not expose signatures, keys, full approval payloads, or digests through the status projection. Receipt validity is audit evidence only; every projection retains `claim=false`, `execution_allowed=false`, and `automatic_import=false`.
