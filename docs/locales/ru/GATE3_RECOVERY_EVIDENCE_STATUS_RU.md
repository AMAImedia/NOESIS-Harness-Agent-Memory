# Gate 3 Recovery Evidence Status — русская локализация

Это supplemental-описание English primary contract для machine-readable recovery evidence status projection. `recovery_evidence_status` оборачивает explicit startup/replay verifier и не превращает verification failures в exceptions для status consumers.

| Ситуация | Status | Claim |
|---|---|---|
| Completion chain и signed snapshot verified | `passed` | `true` |
| Empty event log без completion evidence | `not_run` | `false` |
| Missing, stale, corrupt или invalidly signed evidence | `blocked` | `false` |

Projection всегда содержит schema version, а blocked result — deterministic reason. `blocked` не равно `not_run`: blocked означает, что evidence ожидалась, но не прошла verification; not-run означает, что completion evidence ещё не существует. Projection read-only и не repair-ит event log и не создаёт missing snapshot.

Этот status vocabulary предназначен для operator dashboards, evidence readiness matrices и release reports. Consumers не должны выводить successful recovery, если `claim=false`.

English primary contract: [`GATE3_RECOVERY_EVIDENCE_STATUS.md`](../../GATE3_RECOVERY_EVIDENCE_STATUS.md).
