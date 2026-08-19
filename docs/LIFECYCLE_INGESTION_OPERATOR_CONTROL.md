# Lifecycle Audit Ingestion Operator Control

## Purpose

HealthServer exposes lifecycle audit ingestion status as bounded metadata and provides an authenticated control path at `POST /api/lifecycle-audit-ingestion`. The endpoint accepts `preflight`, `approve`, and `import` actions only when the operator has the `lifecycle:audit:write` scope.

The action handler is operator-controlled and must be explicitly wired to `LifecycleAuditIngestionAdapter`. GET snapshot/readiness/telemetry surfaces cannot trigger ingestion. The HTTP projection forces `automatic_import=false`, `execution_allowed=false`, `claim=false`, and `control=operator_approval_required`, even if an upstream handler returns conflicting values.

| Action | Requirement | Boundary |
|---|---|---|
| `preflight` | Authenticated operator and `lifecycle:audit:write`. | Records evidence as `awaiting_approval`; no import. |
| `approve` | Existing preflight record and explicit operator action. | Creates expiring approval; no import. |
| `import` | Valid non-expired approval and matching digests. | Records `accepted_audit_only`; no execution claim. |

The endpoint is not an external-lane runner. It does not execute providers, child processes, native builds, or comparative tasks.
