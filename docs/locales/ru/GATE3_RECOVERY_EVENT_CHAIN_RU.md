# Gate 3 Recovery Completion-Event Chain — русская локализация

Это supplemental-описание English primary contract для append-only recovery completion-event chain. Каждый новый `execution_recovery_completed` event содержит `previous_event_digest`. Первый event ссылается на `genesis`; каждый следующий — на digest предыдущего completion payload. Audit проходит completion events в append order, проверяет unique action IDs, linked digests и referenced committed completion receipts.

| Условие | Требуемый результат |
|---|---|
| Valid event chain | `status=passed`, count, event IDs, completion receipt IDs и final chain digest. |
| Reordered completion events | Fail-closed с `recovery_completion_event_chain_mismatch`. |
| Duplicate action ID/fork | Fail-closed с `recovery_completion_event_fork`. |
| Malformed completion payload | Fail-closed с `recovery_completion_event_corrupt`. |
| Missing/invalid completion receipt | Fail-closed с `recovery_completion_receipt_invalid`. |
| Non-completion events | Игнорируются projection; не меняют completion chain head. |

Audit является read-only projection над append-only event log. Он не repair-ит, не reorder-ит и не удаляет events. Legacy completion event без `previous_event_digest` может оставаться readable через compatibility paths, но не является valid new chain evidence.

English primary contract: [`GATE3_RECOVERY_EVENT_CHAIN.md`](../../GATE3_RECOVERY_EVENT_CHAIN.md).
