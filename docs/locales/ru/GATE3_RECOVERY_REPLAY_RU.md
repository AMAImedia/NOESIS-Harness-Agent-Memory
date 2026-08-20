# Gate 3 Recovery Replay Assurance — русская локализация

Это supplemental-описание English primary contract для explicit child-runtime recovery после signed artifact-diff receipts. Recovery является **authenticated, receipt-linked, artifact-aware, idempotent** и честным относительно rollback.

## Recovery action binding

Recovery action связывает action ID, operation, run ID, receipt ID, patch proposal, workspace, current base snapshot, operator identity, session identity, scope и optional `artifact_diff_digest`. Полный action mapping fingerprint-ится до execution. Если уже завершённый action ID повторяют с другим payload, recovery fail-closed завершается replay conflict и не считает изменённый запрос idempotent duplicate.

Для rollback stored receipt должен быть signed и recoverable, recovery ledger должен ссылаться на этот receipt, patch должен быть approved для requested workspace и fresh base snapshot, а optional action diff digest должен совпадать с receipt artifact diff digest. Stale receipt, workspace mismatch, stale base, unapproved patch или artifact-diff mismatch отклоняются до вызова injected handler.

| Outcome | Значение |
|---|---|
| `replayed` | Точно такой же authenticated action уже завершён; handler повторно не вызывается. |
| `recovered` | Interrupted run явно resumed и handler подтвердил transition. |
| `rolled_back` | Handler подтвердил rollback, recovery ledger отметил run как rolled back. |
| rejected | Auth, receipt, patch, freshness, digest или handler confirmation failed; success evidence не выпускается. |

Система никогда не заявляет rollback или restoration только потому, что action принят. Injected handler обязан вернуть true; durable recovery state и append-only completion event записываются только после этого подтверждения.

Контракт доказывает только local evidence linkage и bounded recovery state transitions. Native Windows/macOS и external Hermes/OpenCode/DeepSeek Harness recovery остаются `not_run` без matching hosts, exact pinned revisions, disposable environments и signed operator-approved evidence.

English primary contract: [`GATE3_RECOVERY_REPLAY.md`](../../GATE3_RECOVERY_REPLAY.md).
