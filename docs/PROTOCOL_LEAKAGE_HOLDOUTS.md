# Protocol Leakage Holdouts

Normative contract for `ProtocolLeakageSuite` in [`noesis_harness/protocol_leakage_holdouts.py`](../noesis_harness/protocol_leakage_holdouts.py): deterministic protocol/provider leakage holdouts executed over real parallel executor lanes.

## Purpose

The suite proves protocol-boundary hygiene of the multi-agent execution path. Every probe runs through a live `SafeParallelExecutor` lane fan-out ([`noesis_harness/parallel_agent.py`](../noesis_harness/parallel_agent.py)); storage, recall, and coordination never call an LLM. Four fixed cases pin the contract:

| Case id | Probe | Detector |
|---|---|---|
| `event_sink_redaction` | Callback outputs poisoned with a canary value, an absolute workspace path, and an environment value must never reach `event_sink` payloads; clean lanes emit no `error` key and exactly two events per lane. | `redaction_violation` over the sink key envelope plus forbidden-substring search. |
| `audit_error_isolation` | A failing lane's internal token may surface only in that lane's own `result.error`; the executor audit trail and peer results stay clean; peers keep status `passed`. | Recursive value-tree needle search over audit entries and peer results. |
| `result_envelope_typing` | `AgentLaneResult` crosses only its declared typed fields with well-typed values; typed output and typed error strings are preserved exactly. | `envelope_violation`. |
| `cross_session_event_scoping` | Two sequential runs on one shared executor with distinct session ids; a foreign-session marker injected into lane data reaches lane outputs but never events; the second run's events contain neither the foreign marker nor the first run's session id. | `scoping_violation`. |

## Typed contracts

- `SINK_ALLOWED_KEYS = {kind, session_id, task_id, agent_id, error}` — the only keys allowed across the event-sink boundary.
- `RESULT_REQUIRED_KEYS = {status, task_id, agent_id, workspace, output, error}` — subset of the declared `AgentLaneResult` fields.
- `LANE_RESULT_STATUSES = {passed, failed, blocked, cancelled}` — the closed status vocabulary for lane results.
- `ProtocolLeakageResult(case_id, passed, observed)` — one outcome per case; `observed` is `"clean:..."` / `"scoped:..."` on pass or a precise violation code on failure.

Violation vocabulary returned by detectors: `payload[i].extra_keys=...`, `payload[i].forbidden_value=...`, `result[i].extra_fields=...`, `result[i].missing_fields=...`, `result[i].status_unknown=...`, `result[i].{task_id,agent_id,workspace,error,attempts,recovered}_untyped`, `event[i].session_mismatch=...`, `event[i].foreign_session_marker=...`.

## Fail-closed semantics

- Any unexpected exception inside a case classifies that case as failed with observed `unexpected_exception:<Type>`; it is never upgraded to a pass.
- An optional `executor_factory` injects a substitute executor, enabling negative testing against simulated leaky providers (for example, an executor that echoes the workspace root into every sink payload); the suite must detect it.
- Substring detection walks JSON-like value trees directly rather than matching serialized blobs, so Windows backslash paths are caught even though they would be escaped inside a JSON string.
- `summary()` reports `schema_version` (`noesis.protocol-leakage.v1`), per-case outcomes, `total`, `passed`, `failed`, and `pass_rate`; results are deterministic across repeated evaluations.

## Provenance

Patterns borrowed per repo discipline: Hermes/OpenCode observability redaction norms (minimal typed event envelopes, secret-free sinks); deepseek-harness fail-closed evidence handling; the fixed-corpus negative/positive holdout discipline of [`noesis_harness/isolation_holdouts.py`](../noesis_harness/isolation_holdouts.py) (agentmemory-lineage deterministic leakage cases).

## Related tests

- [`tests/test_protocol_leakage_holdouts.py`](../tests/test_protocol_leakage_holdouts.py) — all-holdouts-pass determinism, summary schema, live event-sink payload minimality, leaky-executor negative injection, per-detector unit violations (extra keys/canary, injected field, foreign session), broken factory failing all cases closed.

## Claim boundary

Evidence is local and deterministic only: fixed canaries, temporary local directories, and in-process lane executions scored by pure substring/type checks. A passing summary attests to protocol-boundary hygiene of this code path on this machine at this pinned code state; it is not an external security audit, not a provider-level guarantee, and not evidence about any remote system. No LLM, network access, or wall-clock input participates in scoring.
