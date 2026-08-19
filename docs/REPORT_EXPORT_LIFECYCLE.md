# Report Export Lifecycle Projection

## Purpose

HealthServer exposes the report export lifecycle as bounded read-only metadata for the operator dashboard, snapshot, telemetry, and SSE consumers. The projection observes export state; it cannot start, approve, retry, or cancel an export.

| State | Meaning | Automatic control |
|---|---|---|
| `available` | Export action handler is available and no completed receipt is currently projected. | `false` |
| `approved` | Reserved for an explicit operator-approved action state when an asynchronous executor is introduced. | `false` |
| `exporting` | Reserved for an active operator-triggered export. | `false` |
| `completed` | A signed report export receipt is available. | `false` |
| `blocked` | Lifecycle provider failed or returned invalid data. | `false` |

The projection includes only bounded action/session/output/bundle identifiers. Signing keys, operator tokens, and full receipts are not exposed. The provider forcibly sets `automatic_export=false` and `control=read_only`, even if an upstream provider supplies conflicting values.

The current synchronous executor projects `available` before the first export and `completed` after a signed receipt is appended. `approved` and `exporting` remain reserved states, not claims that an asynchronous operation exists.
