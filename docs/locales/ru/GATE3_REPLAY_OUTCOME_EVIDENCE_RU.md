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

После подтверждённой записи replay snapshot executor атомарно сохраняет signed sidecar `noesis.recovery-replay-snapshot-inventory-snapshot.v1`. Exact replay проверяет durable inventory snapshot против current replay snapshot до возврата `replayed`. Missing, corrupt, path-mismatched, tampered или drifted inventory snapshot fail-closed; во время replay inventory snapshot не создаётся молча заново.

Replay и inventory sidecars являются action-scoped и используют deterministic digest `action_id` в filenames. Recovery-status projection, используемый replay, также action-scoped: две completed actions в одном append-only event log не могут перезаписать replay evidence или status evidence друг друга. Global operator status остаётся отдельным aggregate snapshot.

`audit_replay_evidence_catalog()` — read-only projection со schema `noesis.recovery-replay-evidence-catalog.v1`. Он перечисляет все action-scoped inventory sidecars, проверяет signatures и paths, связывает каждый record с replay snapshot, action event, committed completion receipt и action-scoped status snapshot, а также выпускает deterministic catalog digest. Missing, duplicate, stale, path-conflicting, signature-invalid или identity-conflicting records fail-closed. Exact replay запускает catalog audit до возврата `replayed`.

После проверки catalog executor атомарно сохраняет signed global sidecar `noesis.recovery-replay-evidence-catalog-snapshot.v1`. Exact replay проверяет durable aggregate snapshot против current catalog. Missing, corrupt, path-mismatched, tampered или drifted catalog snapshot блокирует replay и никогда не создаётся молча заново во время replay.

English primary contract: [`GATE3_REPLAY_OUTCOME_EVIDENCE.md`](../../GATE3_REPLAY_OUTCOME_EVIDENCE.md).
