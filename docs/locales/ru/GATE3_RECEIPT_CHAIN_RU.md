# Gate 3 Receipt Chain Audit — русская локализация

Это supplemental-описание English primary contract для проверки ordered immutable execution-receipt history. Chain validator проверяет каждый receipt, отклоняет duplicate receipt IDs, валидирует каждый adjacent lifecycle transition и возвращает deterministic chain digest.

## Chain rules

| Условие | Требуемый результат |
|---|---|
| Valid ordered history | `status=passed`, count, first/last receipt IDs и chain digest. |
| Lifecycle gap | Fail-closed; например `prepared → rolled_back` invalid. |
| Reordering | Fail-closed, если adjacent outcomes больше не образуют allowed transition. |
| Fork/duplicate | Fail-closed при повторном receipt ID. |
| Signature или field tampering | Fail-closed до выпуска chain evidence. |
| Empty или non-tuple history | Fail-closed с `receipt_chain_required`. |

Chain является append-only и не мутирует receipts. Его digest включает ordered receipt ID, outcome и receipt digest каждой entry. Это даёт stable local evidence summary и сохраняет отдельные receipt, artifact-diff, recovery и terminal lifecycle checks.

English primary contract: [`GATE3_RECEIPT_CHAIN.md`](../../GATE3_RECEIPT_CHAIN.md).
