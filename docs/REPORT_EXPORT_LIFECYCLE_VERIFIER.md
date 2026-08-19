# Report Export Lifecycle Evidence Verifier

## Purpose

`verify_lifecycle_events()` and `verify_lifecycle_file()` validate signed `noesis.report-export-lifecycle-event.v1` records before they are used as audit evidence. The verifier checks schema, required identity, HMAC signature, duplicate event IDs, per-session/action grouping, and lifecycle ordering.

A valid lifecycle log produces `status=passed` only for audit verification. `lifecycle_audit_only_projection()` always returns `claim=false`, `execution_claim=false`, and `comparative_claim=false`. Lifecycle events cannot satisfy the signed execution lanes required by the comparative aggregator.

| Rejection | Result |
|---|---|
| Invalid JSON/schema/identity | `blocked` |
| Signature tamper or wrong key | `blocked` |
| Duplicate event ID | `blocked` |
| Invalid action/session ordering | `blocked` |
| Empty input | `not_run` |
| Valid signed lifecycle log | `passed`, audit-only |

A replayed action may have a terminal `blocked` event after an earlier completed sequence; it does not create a second completed receipt and does not upgrade any comparative claim.

`lifecycle_audit_readiness()` exposes this verified result as the separate `report_export_lifecycle_audit` domain. It always reports `execution_lane_satisfied=false`, `native_lane_satisfied=false`, and `external_lane_satisfied=false`, even when the audit log verifies successfully. HealthServer projects the same domain into operator snapshot, telemetry, SSE-related readiness, and `/api/readiness`.
