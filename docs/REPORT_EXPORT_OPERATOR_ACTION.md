# Authenticated Operator Report Export Action

## Purpose

`POST /api/report-export` is the operator-owned control path for exporting a bounded HealthServer snapshot into a signed report bundle. GET snapshot, readiness, telemetry, and SSE surfaces remain read-only.

The action uses `noesis.report-export-action.v1`, requires the `report:export` scope, binds the operator/session, output filename, and exact snapshot digest, and is signed with HMAC-SHA256. The executor persists a single-use `noesis.report-export-receipt.v1` audit record.

| Guard | Failure behavior |
|---|---|
| Missing operator context or handler | `403`/`405`; no export. |
| Wrong operator or missing scope | Rejected before snapshot/export. |
| Signature or schema failure | Rejected before export. |
| Snapshot digest drift | Rejected before writing a bundle. |
| Path traversal or non-ZIP output name | Rejected before writing. |
| Replayed action ID | Rejected; no second bundle or receipt. |
| Provider exception | No successful receipt is emitted. |

The handler calls only the offline snapshot exporter. It does not run external lanes, providers, child processes, or native builds. The signed bundle remains an export artifact with `claim=false`; it is not an approval, execution receipt, or comparative score.
