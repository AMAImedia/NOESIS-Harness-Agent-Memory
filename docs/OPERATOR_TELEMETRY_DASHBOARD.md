# Operator Telemetry Dashboard Contract

The local operator dashboard exposes a read-only telemetry surface for SSE streams and child runtimes. It is an observability view, not a command channel.

| Endpoint | Method | Contract |
|---|---|---|
| `/api/telemetry` | `GET` | Current redacted snapshot of streams, child runtimes and counters. |
| `/api/child-runtimes` | `GET` | Current child-runtime subset and counters. |
| `/api/telemetry/events` | `GET` | Bounded SSE snapshot with `event: telemetry`; the client reconnects to refresh the snapshot. |
| `/api/operator/snapshot` | `GET` | Authenticated read-only operator view including bounded session lane states and execution receipt metadata. |

Telemetry records are recursively redacted for secret-shaped keys, including tokens, credentials, authorization, API keys, passwords and private keys. The dashboard never receives provider credentials, raw authorization headers or hidden memory.

The current implementation intentionally uses a bounded SSE snapshot rather than an unbounded server-side queue. This prevents an idle browser from accumulating unbounded memory. A producer may call `HealthServer.set_telemetry()` with stream and child-runtime records; the server replaces the snapshot atomically under a lock.

The dashboard displays active stream and child-runtime counters, state details and reconnect status. Operator callers may add bounded `task_id` and `receipt_id` query parameters to `/api/operator/snapshot`, `/api/telemetry` and `/api/telemetry/events`; filtering is applied only inside the configured operator session. The session view returns deterministic `lane_counts` by task state and echoes the active filter in the read-only response.
When an authenticated operator session is configured, the telemetry snapshot also includes at most 50 lane states and at most 50 durable execution-evidence records containing only task ID, request ID, receipt ID, committed outcome and sandboxed flag. It never includes task titles, messages, stdout/stderr, workspace paths or receipt-store objects. If the session store is unavailable, the view reports a bounded unavailable reason rather than fabricating lane state.

It does not provide tool execution, provider invocation, arbitrary commands, LAN exposure or approval bypass. The server remains loopback-only by default, and the existing authentication and non-loopback warning gates apply to telemetry endpoints.

The implementation is stdlib-only and is embedded in `noesis_harness/ui_assets.py`. Contract tests cover endpoint shape, SSE framing, read-only behavior and secret redaction.
