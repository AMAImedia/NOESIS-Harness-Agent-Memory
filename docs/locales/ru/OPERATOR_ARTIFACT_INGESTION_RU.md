# Operator Artifact Ingestion Lifecycle

Operator artifact lifecycle реализован в `scripts/operator_ingestion.py`. Он разделяет readiness preflight, explicit human approval и signed artifact import с provider execution. Ledger использует append-only SQLite/WAL state и показывает только bounded status metadata.

| State | Значение | External execution |
|---|---|---|
| `awaiting_approval` | Bundle preflight пройден и ожидает explicit operator decision. | Не запускался. |
| `approved` | Short-lived HMAC approval связан с record, bundle digest и manifest digest. | Ledger всё ещё не запускает provider. |
| `imported` | Signed import принят или принят как `accepted_not_run`. | Import не запускает provider. |
| `blocked` | Bundle preflight или evidence validation failed. | Denied. |
| `rejected` | Approval stale, tampered или связан с другим record. | Denied. |

Lifecycle enforce-ит следующие invariants. Preflight не может выполнить provider. Import требует exact approved record и matching bundle/manifest digests. Approval receipts short-lived и HMAC-bound. Duplicate import после terminal state отклоняется. Imported result сохраняет `score_claim=false` и `external_execution_claim=false`. Provider execution, если когда-либо выполняется, остаётся отдельной командой с собственным pinned-runner approval contract.

Operator status можно передать authenticated read-only HealthServer import-validation provider; тогда он попадает в snapshot/UI/SSE с существующими redaction и bounds. UI и SSE не меняют lifecycle state.

*Supplemental language: Russian.*
