# Report Export SSE Lifecycle Contract

## Purpose

An operator-triggered report export emits bounded lifecycle events to the session SSE stream. The events are observations only; SSE consumers cannot start or approve an export.

For a valid operator action, the event order is:

`approved → exporting → completed`

If authorization, snapshot binding, output policy, or export fails after the action is received, the terminal event is `blocked` and no successful receipt is emitted. Every event includes only session/action identity, status, a bounded reason, `automatic_export=false`, and `control=read_only`.

| Event | Emission point |
|---|---|
| `approved` | After schema, operator, scope, signature, replay and output-name checks. |
| `exporting` | After snapshot provider returns a mapping and before bundle writing. |
| `completed` | After bundle and signed audit receipt are durably written. |
| `blocked` | When a report export action fails closed. |

Events use the existing `noesis.session-stream.v1` bounded buffer and Last-Event-ID reconnect contract. Each lifecycle event is also appended to a separate signed `noesis.report-export-lifecycle-event.v1` JSONL evidence log; the completed receipt log remains separate. Signing keys, operator tokens, snapshots, full receipts and filesystem paths are not emitted. Replayed actions may produce a signed `blocked` lifecycle event, but never a second completed receipt.
