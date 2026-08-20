# Gate 3 Recovery Completion Receipts — русская локализация

Это supplemental-описание English primary contract для recovery completion evidence. После подтверждения mutation injected recovery handler и записи terminal state в recovery store executor создаёт и сохраняет signed execution receipt с `outcome=committed` и recovery-specific side-effect marker.

Completion receipt связывает recovery action mapping, run ID, policy scope, operator identity, optional chain snapshot reference, workspace state и artifact-diff digest. Append-only completion event сохраняет completion receipt ID. При exact replay executor проверяет, что referenced completion receipt существует и остаётся valid committed receipt, прежде чем вернуть `replayed`.

| Условие | Требуемый результат |
|---|---|
| Handler подтверждает и state transition успешен | Signed completion receipt сохраняется, затем event содержит его ID. |
| Handler отсутствует или возвращает false | Committed completion receipt и successful recovery claim не создаются. |
| Exact replay с valid completion receipt | Возвращается `replayed` и existing event result. |
| Event completion-receipt reference tampered | Fail-closed с `recovery_completion_receipt_invalid`. |
| Changed action payload под тем же action ID | Fail-closed с `recovery_action_replay_conflict`. |
| Completion receipt payload/signature tampered | Fail-closed через receipt-store verification. |

Контракт делает recovery success auditable и не считает одну event-log line доказательством. Legacy events без completion receipt reference остаются readable для compatibility, но новые recovery completions всегда содержат signed receipt reference.

English primary contract: [`GATE3_RECOVERY_COMPLETION_RECEIPTS.md`](../../GATE3_RECOVERY_COMPLETION_RECEIPTS.md).
