# Gate 3 Durable Recovery Event-Chain Snapshots — русская локализация

Это supplemental-описание English primary contract для signed sidecar snapshot recovery completion-event chain. После каждого successful recovery completion executor проектирует append-only completion events, подписывает canonical snapshot ключом receipt store и записывает его через atomic temporary-file replacement.

`verify_completion_event_snapshot` повторно открывает sidecar, проверяет HMAC, audit-ит current event chain и сравнивает event IDs, completion receipt IDs, count, event path и chain digest. Snapshot никогда не получает `passed`, если sidecar malformed, signature invalid или current event log drifted.

| Условие | Требуемый результат |
|---|---|
| Successful completion | Signed snapshot atomic replace выполняется после append completion event. |
| Reopen без изменения event log | `status=passed` с теми же payload и signature. |
| Sidecar payload/signature tampering | Fail-closed с `recovery_event_snapshot_signature_invalid` или `recovery_event_snapshot_corrupt`. |
| Event log reorder/corruption | Fail-closed через completion-event chain audit. |
| Stale snapshot против нового event log | Fail-closed с `recovery_event_snapshot_drift`. |
| Partial temporary write | Temporary file не считается canonical snapshot. |

Snapshot является signed projection, а не заменой append-only event log. Реализация не repair-ит, не truncate-ит, не reorder-ит и не rebasing-ит event history silently.

English primary contract: [`GATE3_EVENT_CHAIN_SNAPSHOTS.md`](../../GATE3_EVENT_CHAIN_SNAPSHOTS.md).
