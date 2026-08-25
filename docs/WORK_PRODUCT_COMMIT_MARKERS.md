# Work Product Commit Markers

Normative contract for the durable, append-only ledger of explicit task commit markers (`WorkProductCommitMarkerLedger` in [`noesis_harness/work_product_benchmark.py`](../noesis_harness/work_product_benchmark.py)) and its binding into the governed multi-agent workflow ([`noesis_harness/multi_agent_workflow.py`](../noesis_harness/multi_agent_workflow.py)).

## Purpose

A commit marker is a typed, content-addressed record that states: "this exact reviewed work product was committed for this task by this agent under this merge authorization." The ledger turns that statement into a replayable durable fact that survives process restarts and is independent of (and cross-checkable against) the coordination event log.

## Marker identity and storage

| Field | Meaning |
|---|---|
| `product_id` | Content-addressed id of the reviewed `WorkProductEnvelope`. |
| `task_id`, `agent_id`, `workspace_id` | Delegation identity bound at submit time. |
| `base_snapshot_id`, `head_snapshot_id` | Workspace snapshot pair the review approved. |
| `artifact_digest` | SHA-256 digest of the head snapshot artifact set. |
| `authorization_digest` | Digest of the reviewer-issued `MergeAuthorization`. |
| `schema_version` | Pinned to `noesis.work-product-commit-marker.v1`. |

- `marker_id` = `"marker:" + sha256(canonical JSON of all fields)[:32]`; it is deterministic and recomputable from payload alone.
- Storage reuses [`noesis_harness/event_store.py`](../noesis_harness/event_store.py): append-only JSONL with one event per marker, event type `work_product_commit_marker`, `event_id == marker_id`.
- Invariant: at most one marker per `product_id`, forever.

## Workflow binding

- `MultiAgentWorkProductLoop.commit()` builds a marker from the envelope plus `MergeAuthorization.authorization_digest` and records it **before** transitioning the task to `committed` and before appending `work_product_committed`. Any ledger failure raises `WorkProductError`; the task stays in `review` and no commit event exists.
- `MultiAgentWorkProductLoop.resume()` adds a `commit_markers` projection (`{"count": n, "last_marker_id": ...}`) when a ledger is attached; reopening with the same ledger path yields an identical projection.
- The ledger is optional (`marker_ledger=None`); without it, commit/resume keep their previous behavior and emit no `commit_markers` key.

## Typed statuses

`CommitMarkerRecord(status, marker_id, duplicate)`:

| Status | Duplicate flag | Semantics |
|---|---|---|
| `committed` | `False` | First durable append of this marker. |
| `replayed` | `True` | Identical double-send absorbed as a no-op; nothing new written. |

Error codes raised as `WorkProductBenchmarkError` / `WorkProductError`: `<field>_required`, `unsupported_commit_marker_schema`, `commit_marker_payload_invalid`, `commit_marker_type_required`, `commit_marker_conflict`, `commit_marker_tampered`, `ledger_unexpected_event:<type>`, `ledger_conflict_on_replay`.

## Idempotency and fail-closed semantics

- Double-send of an identical marker returns status `replayed`; exactly one physical log line exists.
- Re-committing the same `product_id` with any differing field raises `commit_marker_conflict` (both in-process and on replay). Divergence is denied, never rewritten.
- Replay-time validation fails closed on: an unexpected event type, a malformed or foreign payload, a stored `event_id` that does not match the recomputed `marker_id` (`commit_marker_tampered`), or two different markers for one product.
- Only a torn final line (crash during append) is repaired on reopen; corruption before the tail is fatal.
- `verify_integrity()` re-reads the entire durable log and validates every record; it returns `{"ok": True, "markers": n, "records": m, "schema_version": ...}` or raises.

## Provenance

Patterns borrowed per repo discipline: LoopX append-only, fingerprint-idempotent event-sourced state via `event_store.py`; agentmemory governance write semantics (identical resend is a replay, identity/content divergence is denied, never rewritten); deepseek-harness bounded deterministic rubric for the sibling `WorkProductBenchmarkEvaluator` in the same module.

## Related tests

- [`tests/test_work_product_gate4_gap.py`](../tests/test_work_product_gate4_gap.py) — double-send absorption, restart replay, torn-tail repair, mid-file tampering rejection, foreign event/payload rejection, integrity report, loop-level Gate 4 locks.
- [`tests/test_multi_agent_workflow_markers.py`](../tests/test_multi_agent_workflow_markers.py) — commit/resume binding, exactly-one-marker invariant, forged authorization fails closed leaving task in `review`, resume projection stability across reopen, `None`-ledger legacy path.
- [`tests/test_work_product_benchmark.py`](../tests/test_work_product_benchmark.py) — sibling evaluator metric determinism and fail-closed input validation.

## Claim boundary

Evidence produced here is local and deterministic only: SHA-256 identities over canonical JSON and a replay projection of a local JSONL log. A verified ledger attests that markers were recorded and remain locally re-verifiable; it does not prove external merge application (`files_applied` remains `False`), reviewer intent, or the state of any external system. No LLM, network access, randomness, or wall-clock input participates in recording or verification.
