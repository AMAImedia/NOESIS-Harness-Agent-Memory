# Gate 3 Recovery Evidence Startup Verification — русская локализация

Это supplemental-описание English primary contract для startup и replay verification recovery evidence. `verify_recovery_evidence` audit-ит append-only completion-event chain и затем проверяет его signed durable sidecar snapshot.

Пустой event log без snapshot является valid no-op и возвращает `snapshot.status=not_run` с reason `no_completion_events`. После появления completion event missing snapshot не допускается silently: verification fail-closed с `recovery_event_snapshot_missing`. Existing snapshot должен пройти HMAC validation и совпасть с current event IDs, completion receipt IDs, count, event path и chain digest.

| Условие | Требуемый результат |
|---|---|
| Empty event log без snapshot | Passed no-op; recovery completion evidence не заявляется. |
| Non-empty event log с valid snapshot | Passed chain и snapshot evidence. |
| Non-empty event log без snapshot | Fail-closed с `recovery_event_snapshot_missing`. |
| Snapshot corrupt/signature-invalid | Fail-closed через snapshot verification. |
| Snapshot stale против current log | Fail-closed с `recovery_event_snapshot_drift`. |
| Event chain reordered/forked | Fail-closed через completion-event chain audit. |

Это explicit operator/startup gate, а не automatic repair mechanism. Verifier не создаёт missing snapshot, не переписывает event history и не переводит `not_run` в `passed` без durable evidence.

English primary contract: [`GATE3_RECOVERY_EVIDENCE_STARTUP.md`](../../GATE3_RECOVERY_EVIDENCE_STARTUP.md).
