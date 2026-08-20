# Gate 3 Recovery Status Snapshots — русская локализация

Это supplemental-описание English primary contract для signed persistent machine-readable recovery-status snapshot. После каждого successful recovery completion executor сохраняет derived status projection рядом с event-chain snapshot через atomic temporary-file replacement. Status payload содержит schema version, event path, status, claim flag, reason и current chain digest.

`verify_recovery_evidence_status_snapshot` повторно открывает sidecar, проверяет HMAC, пересчитывает current status projection и сравнивает все bound fields. Tampered signature, malformed sidecar или изменение underlying evidence fail-closed вместо возврата stale status.

| Условие | Требуемый результат |
|---|---|
| Valid `passed` projection | Signed snapshot verified с `claim=true`. |
| Valid `not_run` projection | Signed snapshot может быть сохранён явно с `claim=false`; success не подразумевается. |
| Valid `blocked` projection | Signed snapshot может сохранять deterministic failure reason с `claim=false`. |
| Sidecar tampering/malformed JSON | Fail-closed с status-snapshot corruption/signature error. |
| Изменение underlying event/snapshot state | Fail-closed с `recovery_status_snapshot_drift`. |
| Atomic write interruption | Temporary file не считается canonical status snapshot. |

Status snapshot является signed projection, а не authorization token и не заменяет event-chain evidence. Consumers должны повторно проверить его перед recovery claim.

English primary contract: [`GATE3_RECOVERY_STATUS_SNAPSHOTS.md`](../../GATE3_RECOVERY_STATUS_SNAPSHOTS.md).
