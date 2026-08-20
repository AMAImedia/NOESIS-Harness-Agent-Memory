# Gate 3 Persistent Receipt-Chain Snapshots — русская локализация

Это supplemental-описание English primary contract для хранения и reopen durable receipt-chain evidence. `ExecutionReceiptStore.save_chain_snapshot` сначала проверяет ordered chain, вычисляет deterministic snapshot ID из ordered receipt IDs и chain digest и idempotently сохраняет snapshot в SQLite/WAL storage.

`get_chain_snapshot` проверяет stored snapshot payload, пересчитывает snapshot digest, загружает referenced receipts и сравнивает current chain digest с persisted value. Snapshot никогда не получает `passed`, если payload malformed, reference missing или current receipt chain drifted.

| Условие | Требуемый результат |
|---|---|
| First valid save | Один deterministic snapshot сохраняется и возвращается с `status=passed`. |
| Exact repeated save | Возвращается тот же snapshot без duplicate rows или mutation. |
| Database reopen | Тот же snapshot ID повторно открывается и сверяется с current receipts. |
| Snapshot payload corruption | Fail-closed с `receipt_chain_snapshot_tampered`. |
| Missing snapshot | Fail-closed с `receipt_chain_snapshot_missing`. |
| Missing referenced receipt | Fail-closed через durable chain loader. |
| Current chain digest drift | Fail-closed с `receipt_chain_snapshot_drift`. |

Snapshot является evidence для конкретного ordered receipt set, а не заменой underlying receipts. Storage остаётся append-only; snapshot API не repair-ит, не переписывает и не rebinding-ит missing или changed references.

English primary contract: [`GATE3_CHAIN_SNAPSHOTS.md`](../../GATE3_CHAIN_SNAPSHOTS.md).
