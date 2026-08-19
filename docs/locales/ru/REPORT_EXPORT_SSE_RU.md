# Контракт SSE lifecycle report export

## Назначение

Operator-triggered report export отправляет bounded lifecycle events в session SSE stream. Events являются только наблюдением; SSE consumers не могут запустить или утвердить export.

Для корректной operator action порядок событий такой:

`approved → exporting → completed`

Если authorization, snapshot binding, output policy или export завершается ошибкой после получения action, terminal event — `blocked`, а успешный receipt не создаётся. Каждое событие содержит только session/action identity, status, ограниченный reason, `automatic_export=false` и `control=read_only`.

| Event | Момент отправки |
|---|---|
| `approved` | После schema, operator, scope, signature, replay и output-name checks. |
| `exporting` | После того как snapshot provider вернул mapping и до записи bundle. |
| `completed` | После durable записи bundle и signed audit receipt. |
| `blocked` | Когда report export action fail-closed отклонена. |

Events используют существующий bounded `noesis.session-stream.v1` buffer и Last-Event-ID reconnect contract. Каждый lifecycle event также append-ится в отдельный signed `noesis.report-export-lifecycle-event.v1` JSONL evidence log; completed receipt log остаётся отдельным. Signing keys, operator tokens, snapshots, full receipts и filesystem paths не отправляются. Replayed action может создать signed `blocked` lifecycle event, но никогда не создаёт второй completed receipt.

Authenticated `POST /api/report-export` принимает signed `noesis.report-export-action.v1` mapping. Поле `receipt_audit_path` optional и, если задано, входит в signed action identity. До authorization completion оно должно указывать на существующий absolute `.json` file; executor проверяет record identity и все receipts тем же operator signing key до записи archive. Без path создаётся backward-compatible v1 export. С verified path выбирается v2 и добавляется только normalized audit-only domain `lifecycle_receipt_audit`. Invalid, stale, tampered или unverifiable input даёт `blocked` и не создаёт successful receipt.
