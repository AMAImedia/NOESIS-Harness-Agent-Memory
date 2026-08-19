# Operator Telemetry Dashboard Contract

Локальный operator dashboard предоставляет read-only telemetry surface для SSE streams и child runtimes. Это observability view, а не command channel.

| Endpoint | Method | Contract |
|---|---|---|
| `/api/telemetry` | `GET` | Текущий redacted snapshot streams, child runtimes и counters. |
| `/api/child-runtimes` | `GET` | Подмножество child-runtime и counters. |
| `/api/telemetry/events` | `GET` | Bounded SSE snapshot с `event: telemetry`; client reconnects для обновления snapshot. |
| `/api/operator/snapshot` | `GET` | Authenticated read-only operator view с bounded session lane states и execution receipt metadata. |

Telemetry records recursively redacted для secret-shaped keys: tokens, credentials, authorization, API keys, passwords и private keys. Dashboard не получает provider credentials, raw authorization headers или hidden memory.

Реализация намеренно использует bounded SSE snapshot вместо unbounded server-side queue. Это не позволяет idle browser накапливать неограниченную память. Producer может вызвать `HealthServer.set_telemetry()` с stream и child-runtime records; server atomically заменяет snapshot под lock.

Dashboard показывает counters active streams/child runtimes, state details и reconnect status. Operator может добавить bounded query parameters `task_id` и `receipt_id` к `/api/operator/snapshot`, `/api/telemetry` и `/api/telemetry/events`; filtering работает только внутри настроенной operator session. Session view возвращает deterministic `lane_counts` по task state и отражает активный filter в read-only response.
 При настроенной authenticated operator session telemetry snapshot дополнительно содержит не более 50 lane states и не более 50 durable execution-evidence records: только task ID, request ID, receipt ID, committed outcome и sandboxed flag. В него не попадают task titles, messages, stdout/stderr, workspace paths или receipt-store objects. Если session store недоступен, view сообщает bounded unavailable reason и не выдумывает lane state.

Тот же snapshot может содержать `import_validation` со статусом `blocked`, `accepted_not_run`, `accepted` или `unavailable` и максимум 32 redacted drift/error reasons. Projection принудительно возвращает `score_claim=false` и `external_execution_claim=false`, даже если upstream provider прислал другие значения. Это только telemetry: UI и SSE не предоставляют import action, provider command, approval consumption или score mutation.

Dashboard не предоставляет tool execution, provider invocation, arbitrary commands, LAN exposure или approval bypass. Server по умолчанию остаётся loopback-only; для telemetry действуют существующие authentication и non-loopback warning gates.

English primary contract: [`OPERATOR_TELEMETRY_DASHBOARD.md`](../../OPERATOR_TELEMETRY_DASHBOARD.md).
