# Operator Artifact Ingestion Lifecycle

The operator artifact lifecycle is implemented by `scripts/operator_ingestion.py`. It separates readiness preflight, explicit human approval and signed artifact import from provider execution. The ledger is append-only SQLite/WAL state and exposes only bounded status metadata.

| State | Meaning | External execution |
|---|---|---|
| `awaiting_approval` | Bundle preflight passed and waits for an explicit operator decision. | Never started. |
| `approved` | A short-lived HMAC approval is bound to the record, bundle digest and manifest digest. | Still never started by this ledger. |
| `imported` | Signed import was accepted or accepted as `accepted_not_run`. | Never started by import. |
| `blocked` | Bundle preflight or evidence validation failed. | Denied. |
| `rejected` | Approval was stale, tampered or bound to another record. | Denied. |

The lifecycle enforces the following invariants. Preflight cannot execute a provider. Import requires the exact approved record and matching bundle/manifest digests. Approval receipts are short-lived and HMAC-bound. Duplicate import after terminal state is rejected. Imported results retain `score_claim=false` and `external_execution_claim=false`. Provider execution, if ever performed, remains a separate command requiring its own pinned-runner approval contract.

The operator status can be supplied to the authenticated read-only HealthServer import-validation provider, where it is projected to the snapshot/UI/SSE surface with the existing redaction and bounds. No UI or SSE endpoint changes lifecycle state.

*Primary language: English.*
