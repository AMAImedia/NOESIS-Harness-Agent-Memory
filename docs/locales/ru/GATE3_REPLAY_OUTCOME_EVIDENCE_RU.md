# Gate 3 Replay Outcome Evidence — русская локализация

Это supplemental-описание English primary contract для machine-readable evidence, возвращаемого exact recovery replay. Replay result содержит projection `noesis.recovery-replay-evidence.v1`, связывающий action ID и action digest с committed completion receipt и verified persistent recovery-status snapshot.

| Поле | Значение |
|---|---|
| `status` | `passed` только после проверки всего bound evidence. |
| `claim` | `true` только для полностью проверенного exact replay. |
| `action_id` / `action_digest` | Identity и canonical request binding replayed action. |
| `completion_receipt_id` | Reference на immutable committed recovery completion receipt. |
| `status_snapshot_digest` | Digest verified status snapshot payload. |

`audit_replay_outcome()` является read-only. Он не создаёт receipt, не repair-ит snapshot, не применяет rollback и не превращает unavailable evidence в `not_run`. Missing, stale, corrupt или mismatched evidence fail-closed. Exact replay idempotent только пока весь evidence set не изменён.

English primary contract: [`GATE3_REPLAY_OUTCOME_EVIDENCE.md`](../../GATE3_REPLAY_OUTCOME_EVIDENCE.md).
