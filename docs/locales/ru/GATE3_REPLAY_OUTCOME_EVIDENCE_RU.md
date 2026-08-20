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

Последней записью является signed `noesis.recovery-replay-evidence-commit-manifest.v1` для каждой action. Он связывает action, committed completion receipt, action-scoped status/replay/inventory snapshots, global catalog snapshot и stable per-action completeness-record digest. При добавлении новой action implementation может сначала записать provisional manifest, затем обновить completeness snapshot и атомарно перезаписать manifest как final durable write. Exact replay проверяет этот final manifest последним: partial evidence bundle не может стать `replayed`; missing, corrupt, path-mismatched, tampered или drifted manifest fail-closed без repair.

`audit_replay_evidence_completeness()` — read-only startup-style audit со schema `noesis.recovery-replay-evidence-completeness.v1`. Он требует один valid action-scoped commit manifest на каждый completed recovery event, проверяет receipt identity и manifest paths, а также требует равенства manifest count, event count и catalog count. Missing, duplicate, corrupt, conflicting или uncommitted completion блокирует completeness claim.

Completeness projection также сохраняется как signed `noesis.recovery-replay-evidence-completeness-snapshot.v1`. Exact replay проверяет durable claim против current bundle после commit manifest gate. Missing, corrupt, path-mismatched, tampered или drifted completeness snapshot fail-closed и никогда не создаётся молча заново во время replay.

До promotion любого replay evidence в `replayed` executor проверяет signed `noesis.recovery-event-chain-snapshot.v1` против append-only completion event log. Эта проверка выполняется до action-scoped status verification, поэтому missing или drifted chain evidence сообщает direct chain denial. Duplicate JSON keys в chain snapshot отклоняются.

Action replay projection также проверяет completion-event prefix target action и требует, чтобы его final committed receipt ID совпадал с completion receipt ID replay record. Полученный `event_chain_digest` входит в signed replay evidence snapshot и не позволяет replay against different committed completion event.

Final commit manifest дополнительно содержит deterministic `bundle_digest` по canonical action-scoped fields. Verification пересчитывает digest до принятия manifest и связывает status, replay, inventory, catalog, completeness, receipt и path projections как единый evidence bundle.

English primary contract: [`GATE3_REPLAY_OUTCOME_EVIDENCE.md`](../../GATE3_REPLAY_OUTCOME_EVIDENCE.md).
