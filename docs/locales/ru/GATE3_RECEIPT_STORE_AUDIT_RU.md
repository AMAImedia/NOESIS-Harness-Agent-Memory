# Gate 3 Receipt Store Audit — русская локализация

Это supplemental-описание English primary contract для аудита durable execution receipt store. Audit загружает каждый stored payload в deterministic `receipt_id` order, восстанавливает receipt, проверяет schema, digest, HMAC signature и database identity binding, затем возвращает stable integrity snapshot.

| Условие | Требуемый результат |
|---|---|
| Все stored receipts valid | `status=passed`, count, sorted receipt IDs и aggregate payload digest. |
| Exact database reopen | Тот же набор receipts даёт тот же audit snapshot и aggregate digest. |
| Malformed JSON или missing fields | Fail-closed с `stored_receipt_tampered`. |
| Invalid digest или HMAC | Fail-closed с `stored_receipt_tampered`. |
| Row key отличается от receipt ID | Fail-closed с `stored_receipt_identity_mismatch`. |
| Duplicate `put` с тем же payload | No-op; возвращается existing receipt. |
| Duplicate `put` с другим payload | Fail-closed с `receipt_conflict`. |

Audit является только local evidence integrity receipt store. Он не доказывает process isolation, artifact restoration или availability external/native execution. Эти lanes остаются отдельно классифицированными как `not_run` до появления required environments и signed evidence.

English primary contract: [`GATE3_RECEIPT_STORE_AUDIT.md`](../../GATE3_RECEIPT_STORE_AUDIT.md).
