# Gate 3 Snapshot-to-Recovery Link — русская локализация

Это supplemental-описание English primary contract для binding explicit recovery action с persisted receipt-chain snapshot. Rollback action может содержать `chain_snapshot_id`; до вызова injected rollback handler executor повторно открывает и проверяет snapshot и требует target receipt ID в его ordered receipt set.

Snapshot reference входит в deterministic action fingerprint. Поэтому изменение или удаление reference под тем же `action_id` является replay conflict, а не silent retry. Missing, malformed, stale или unrelated snapshot fail-closed до mutation.

| Условие | Требуемый результат |
|---|---|
| Valid snapshot содержит target receipt | Handler может выполняться после authorization и patch checks. |
| Snapshot missing/corrupted | Fail-closed через snapshot verification. |
| Snapshot не содержит target receipt | Fail-closed с `recovery_chain_snapshot_mismatch`. |
| Same action ID с другим snapshot reference | Fail-closed с `recovery_action_replay_conflict`. |
| Successful rollback | Completion receipt содержит snapshot ID и snapshot digest. |
| Handler отсутствует или возвращает false | Recovery mutation не заявляется. |

Link объединяет signed execution receipts, durable chain snapshots, capability-scoped recovery authorization, artifact-diff checks и append-only completion events. Он не выводит lifecycle truth из workspace names, patch IDs или current filesystem state.

English primary contract: [`GATE3_SNAPSHOT_RECOVERY_LINK.md`](../../GATE3_SNAPSHOT_RECOVERY_LINK.md).
