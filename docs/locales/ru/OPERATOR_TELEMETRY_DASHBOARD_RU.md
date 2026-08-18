# Operator Telemetry Dashboard Contract

Локальный operator dashboard предоставляет read-only telemetry surface для SSE streams и child runtimes. Это observability view, а не command channel.

| Endpoint | Method | Contract |
|---|---|---|
| `/api/telemetry` | `GET` | Текущий redacted snapshot streams, child runtimes и counters. |
| `/api/child-runtimes` | `GET` | Подмножество child-runtime и counters. |
| `/api/telemetry/events` | `GET` | Bounded SSE snapshot с `event: telemetry`; client reconnects для обновления snapshot. |

Telemetry records recursively redacted для secret-shaped keys: tokens, credentials, authorization, API keys, passwords и private keys. Dashboard не получает provider credentials, raw authorization headers или hidden memory.

Реализация намеренно использует bounded SSE snapshot вместо unbounded server-side queue. Это не позволяет idle browser накапливать неограниченную память. Producer может вызвать `HealthServer.set_telemetry()` с stream и child-runtime records; server atomically заменяет snapshot под lock.

Dashboard показывает counters active streams/child runtimes, state details и reconnect status. Он не предоставляет tool execution, provider invocation, arbitrary commands, LAN exposure или approval bypass. Server по умолчанию остаётся loopback-only; для telemetry действуют существующие authentication и non-loopback warning gates.

English primary contract: [`OPERATOR_TELEMETRY_DASHBOARD.md`](../../OPERATOR_TELEMETRY_DASHBOARD.md).
