# Lifecycle Audit Bundle Ingestion

## Purpose

`LifecycleAuditIngestionAdapter` imports a verified report bundle and its signed lifecycle JSONL audit log into a durable SQLite ledger. It is an audit-only import path. It never executes providers, child runtimes, native builds, or external lanes.

| Stage | Behavior |
|---|---|
| `preflight` | Verifies the deterministic report bundle, verifies every lifecycle signature/order, rejects stale files and duplicate bundle digests, then records `awaiting_approval`. |
| `approved` | Records an explicit operator approval bound to bundle digest, audit digest, operator identity and expiry. |
| `imported` | Records `accepted_audit_only` after approval validation. |
| `blocked` | Used for malformed/tampered/stale/duplicate evidence or unavailable verification. |
| `rejected` | Used for invalid, expired, or identity-mismatched approval. |

The adapter uses a separate schema, `noesis.lifecycle-audit-ingestion.v1`, and durable append-only SQLite events. Every result forces `execution_allowed=false`, `automatic_execution=false`, and `claim=false`. An imported lifecycle audit cannot satisfy `delegated` or `child_runtime` lanes and cannot raise native, external, comparative, or worldwide claims.
