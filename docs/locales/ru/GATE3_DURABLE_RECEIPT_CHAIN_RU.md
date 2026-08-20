# Gate 3 Durable Receipt Chain — русская локализация

Это supplemental-описание English primary contract для проверки ordered receipt chain после reopen durable store. `ExecutionReceiptStore.audit_chain` загружает requested receipt IDs из SQLite/WAL storage, проверяет каждый stored receipt, сохраняет caller-provided order и передаёт chain immutable validator.

| Условие | Требуемый результат |
|---|---|
| Valid stored chain after reopen | `status=passed`, count, first/last IDs и deterministic chain digest. |
| Reversed/reordered IDs | Fail-closed, если adjacent lifecycle transitions становятся invalid. |
| Missing stored entry | Fail-closed с `receipt_chain_missing`; partial passed evidence не выпускается. |
| Stored payload tampering | Fail-closed через receipt signature/digest verification. |
| Duplicate chain entry | Fail-closed через duplicate receipt-ID detection. |
| Store reopen | Те же ordered IDs дают тот же chain result и digest. |

Chain IDs являются explicit ordered evidence input, а не inferred SQL row order. Это предотвращает превращение storage order, insertion timing или partial query в lifecycle truth. Durable store остаётся append-only; audit не мутирует receipts и не восстанавливает missing chain entries.

English primary contract: [`GATE3_DURABLE_RECEIPT_CHAIN.md`](../../GATE3_DURABLE_RECEIPT_CHAIN.md).
