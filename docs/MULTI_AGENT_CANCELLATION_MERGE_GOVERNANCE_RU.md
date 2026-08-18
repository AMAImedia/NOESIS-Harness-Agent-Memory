# Multi-Agent Cancellation и Merge Governance Contract

Этот increment усиливает parallel execution и workspace review boundary. Он не превращает Python threads в OS sandbox: cancellation является **cooperative**, поэтому callback обязан периодически вызывать `ctx.check_cancelled()`.

| Contract | Acceptance criterion |
|---|---|
| Operator cancellation | `CancellationToken.cancel(reason)` приводит cooperative lane к статусу `cancelled` с audit event и reason |
| Wall-time budget | `max_duration_seconds` задаёт deadline; просроченный lane становится `cancelled`, если callback проверяет token |
| Recovery safety | Cancelled/failed action не завершается как `done`; action requeue остаётся доступным владельцу/recovery coordinator |
| Isolation | Cancellation одного lane не отменяет независимые lanes автоматически |
| Review gate | Patch обязан быть `approved` перед merge authorization |
| Independent review | Reviewer обязан быть отдельным non-empty identity |
| Stale-base protection | Authorization отклоняется при несовпадении current base snapshot и proposal base |
| No implicit publish | `authorize_merge` выдаёт signed-style SHA-256 receipt, но не применяет и не публикует изменения |

## Boundary

Для non-cooperative callback процесс нельзя принудительно остановить из Python thread executor; executable tools/skills должны использовать отдельный ChildExecutionRuntime с timeout/process termination. Поэтому локальное evidence не называет thread cancellation полноценным OS kill switch.
