# Operator Evidence Projection Contract

## Purpose

HealthServer exposes signed aggregate evidence as a bounded, read-only projection. The projection helps an operator distinguish local execution evidence from native parity and external comparative readiness; it cannot execute, import, approve, or escalate claims.

The aggregate appears as `evidence_aggregate` in the operator snapshot and telemetry, and in `/api/readiness`. The projection forcibly sets `comparative_claim=false` and labels its boundary as `read_only_evidence_status`, even if an upstream provider supplies stronger-looking fields.

| Surface | Meaning | Control capability |
|---|---|---|
| `evidence_aggregate` | Verified local receipt aggregation status. | Read-only. |
| `migration_readiness` | Operator-owned storage migration status. | Read-only on GET surfaces. |
| Native parity readiness | Matching-host artifact/execution status. | Does not become passed on Linux simulation. |
| External comparative readiness | Exact pinned external lane evidence. | Cannot be populated by local aggregate. |

Provider absence is `not_run`; provider failure is `blocked`. Secrets such as signing keys are not projected. SSE and UI consumers receive the same bounded projection and no mutation action.

> A status projection is an observation boundary. It is not an authorization boundary and cannot turn local evidence into a comparative claim.
