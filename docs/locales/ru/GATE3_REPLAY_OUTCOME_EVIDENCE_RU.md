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

После подтверждённого recovery completion executor атомарно сохраняет signed sidecar `noesis.recovery-replay-evidence-snapshot.v1`. Exact replay обязан проверить этот sidecar против current action, committed receipt и status snapshot. Missing, tampered или drifted replay snapshot отклоняется до возврата результата `replayed`.

`audit_replay_snapshot_inventory()` — deterministic read-only projection со schema `noesis.recovery-replay-snapshot-inventory.v1`. Он фиксирует verified sidecar path, payload digest, action identity, action digest и completion receipt identity. Signed replay snapshot содержит canonical sidecar path; path mismatch отклоняется до inventory projection. Duplicate JSON keys считаются conflicting records; mismatched action identity или completion receipt identity дают explicit identity-conflict error. Повторный audit неизменённого evidence обязан давать byte-equivalent результат; verification failure передаётся fail-closed без частичного inventory.

English primary contract: [`GATE3_REPLAY_OUTCOME_EVIDENCE.md`](../../GATE3_REPLAY_OUTCOME_EVIDENCE.md).
