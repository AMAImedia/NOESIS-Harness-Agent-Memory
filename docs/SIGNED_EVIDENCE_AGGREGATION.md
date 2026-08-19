# Signed Evidence Aggregation Contract

## Purpose

The aggregator combines already-produced delegated and child-runtime evidence without executing a provider, child process, or external lane. It prevents evidence from different sessions, tasks, request identities, or lanes from being mixed into one stronger claim.

## Required record binding

Every record must include `evidence_id`, `lane`, `session_id`, `task_id`, `request_digest`, `status`, a signed `receipt`, and its signature. The receipt must repeat the session, task, request digest, and `status=passed`. The HMAC signature is verified before the record participates in the aggregate digest.

| Condition | Aggregate result |
|---|---|
| No records | `not_run`; no execution claim. |
| Missing required lane | `not_run`; no execution claim. |
| Invalid signature or receipt identity mismatch | `blocked`; no claim. |
| Duplicate evidence ID | `blocked`; no claim. |
| Non-passed receipt | `blocked`; no claim. |
| All required signed records valid | `passed` for evidence verification only. `comparative_claim=false`. |

The default required lanes are `delegated` and `child_runtime`. The aggregate digest is deterministic over normalized records and required lane identities. A verified local aggregate does not produce a Hermes, OpenCode, DeepSeek Harness, native Windows/macOS, or worldwide-superiority claim.

> Aggregation proves that specific receipts are mutually bound and intact; it does not make an unrun lane run, and it does not turn local evidence into external comparative evidence.
