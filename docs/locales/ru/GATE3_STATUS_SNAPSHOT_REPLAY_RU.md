# Gate 3 Status Snapshot Replay Verification — русская локализация

Это supplemental-описание English primary contract для exact recovery replay. Replayed recovery action не принимается только потому, что action fingerprint и committed completion receipt совпадают. Executor также обязан найти и проверить signed persistent recovery-status snapshot против current event-chain evidence.

| Условие replay | Требуемый результат |
|---|---|
| Action fingerprint, completion receipt и status snapshot verified | Вернуть `replayed`. |
| Same action ID с изменённым payload | Fail-closed с `recovery_action_replay_conflict`. |
| Missing/not-committed completion receipt | Fail-closed с `recovery_completion_receipt_invalid`. |
| Missing status snapshot | Fail-closed с `recovery_status_snapshot_missing`. |
| Invalid/stale status snapshot | Fail-closed с соответствующей status-snapshot error. |

Replay path idempotent только для unchanged и fully verifiable evidence set. Он не создаёт missing status snapshot во время replay и не возвращает `replayed`, пока projection stale или corrupted.

English primary contract: [`GATE3_STATUS_SNAPSHOT_REPLAY.md`](../../GATE3_STATUS_SNAPSHOT_REPLAY.md).
