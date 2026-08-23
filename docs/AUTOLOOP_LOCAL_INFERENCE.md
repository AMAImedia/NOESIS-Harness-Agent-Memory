# Local Inference Proposal Loop

The Windows unattended worker supports an **explicit local HTTP inference endpoint** through `NOESIS_AUTOLOOP_LOCAL_ENDPOINT` and `NOESIS_AUTOLOOP_PROMPT_FILE`. The core remains Python stdlib-only: HTTP transport uses `urllib`, and no model-generated text is imported, executed, or promoted automatically.

When both settings are present, each bounded cycle sends a request to the configured endpoint with the local NOESIS chat contract:

```json
{"message":"...","preset":"code","max_tokens":768,"temperature":0.2}
```

The response must be JSON containing a textual `response`, `reply`, `answer`, `text`, `content`, or `message.content` field. Unknown or malformed response shapes fail closed. Responses are capped by the output budget and written atomically under `.noesis_autoloop/artifacts/`. The state record includes `mode: review_only_proposal`, cycle number, request digest, reason, and artifact path.

This path is **proposal-only**. It does not apply patches, execute generated code, merge branches, publish skills, or bypass human-governed promotion. A separate governed review/import pipeline remains required for any change to become active.

## Windows configuration

Set the endpoint and prompt file explicitly in the SYSTEM task environment or in the task wrapper. Do not configure an endpoint by discovery. For the existing local NOESIS server, the endpoint contract is exposed at `POST http://127.0.0.1:8810/api/chat`; readiness and model availability remain separate concerns.

```powershell
[Environment]::SetEnvironmentVariable(
  'NOESIS_AUTOLOOP_LOCAL_ENDPOINT',
  'http://127.0.0.1:8810/api/chat',
  'Machine'
)
[Environment]::SetEnvironmentVariable(
  'NOESIS_AUTOLOOP_PROMPT_FILE',
  'B:\\path\\to\\review_prompt.txt',
  'Machine'
)
```

The endpoint must be loopback or otherwise explicitly trusted by the operator. Authentication is optional in the adapter but, when enabled by the server, the caller must supply a bearer token through a protected task-level configuration; secrets are never written to evidence or logs.

## Verified boundary

The adapter and proposal path are locally implemented and covered by deterministic Windows-compatible tests. A real unattended coding run remains **environment-gated** until the configured endpoint is verified to load a model, return a bounded response, and produce a reviewable artifact under the SYSTEM account. Until then, the worker should remain on validation-only cycles rather than claiming autonomous coding readiness.

## Persistent worker versus agent session

The Windows Scheduled Task is a persistent **worker**, not a persistent Manus agent session. It can execute its bounded validation/recovery loop after the chat session ends, but it cannot receive new planning context, invent a new implementation plan, or perform interactive GitHub development between agent sessions. The worker therefore reports this boundary explicitly rather than implying that an agent remains active.

Run the capability probe without acquiring the worker lock:

```powershell
py -3.11 scripts\noesis_autoloop.py --status
```

The probe returns `noesis.autoloop-capabilities.v1`. Its invariant fields are `agent_session_continuity: false`, `autonomous_code_promotion: false`, and `autonomous_protected_admin_mutation: false`. With no explicit local endpoint and prompt file, the status is `validation_only`; with both configured, it becomes `review_only` and still cannot promote or execute generated code.

This distinction is operationally important: a green worker heartbeat proves only that the configured worker cycle completed. It does not prove that an agent session continued writing code, updating documentation, or synchronizing GitHub after the session ended.

## Evidence contract

The capability probe now emits `boundary_version: protected-actions.v1`, explicit `local_endpoint_configured`, `prompt_file_configured`, and `arbitrary_command_configured` flags, plus a deterministic `evidence_digest` over the public capability payload. Endpoint URLs, prompt paths, command text, and credentials are intentionally excluded from the returned payload and digest. Blank or whitespace-only configuration is treated as unconfigured, so it cannot silently enable proposal mode.

The stable claims are `worker_heartbeat_only`, `no_agent_session_continuity`, and `no_protected_admin_mutation`. These are capability claims, not proof that a model is loaded or that generated code is safe to promote.

## Crash-safe cycle recovery

If the process terminates after persisting a `running` state but before writing `END`, the next cycle does not silently overwrite that evidence. It increments the cycle and records `recovered_previous_cycle` in the `BEGIN` record, final state, and `END` record. This preserves a deterministic link from the interrupted turn to its recovery attempt while keeping the event log append-only.

The recovery marker proves that an interrupted worker cycle was detected; it does not claim that the interrupted child process completed or that any generated proposal was promoted.

The recovery evidence also includes a deterministic `recovery_digest` over only the prior cycle number and its `running` status. This digest deliberately excludes command text, endpoint, prompt path, and credentials. A normal completed cycle has no recovery digest, preventing false claims that recovery occurred.

## Durable log writes

Worker `BEGIN` and `END` evidence lines are flushed and `fsync`-ed before the cycle proceeds. This narrows the crash window: a persisted `running` state has a durable corresponding `BEGIN` line, and a completed result has a durable `END` line before final state publication. The worker still treats filesystem and host power-loss guarantees as environment boundaries; it does not claim transactional durability beyond the host filesystem contract.

## Command evidence redaction

For validation cycles, durable state and `BEGIN` evidence no longer contain the configured command text. They contain only `command_digest` and `command_configured`. This prevents tokens or other command-line secrets from being copied into state and logs while preserving deterministic identity of the selected command.

## Durable proposal queue

An optional `NOESIS_AUTOLOOP_STEPS_FILE` may contain a JSON array of bounded review-only steps. The worker selects `proposal_step_index` deterministically, retries the same step after a failed proposal, and advances the index only after a passed response has been atomically stored as an artifact. An exhausted queue becomes an explicit `idle` result; it does not invent work or execute a hidden fallback command. Queue corruption or an invalid index fails closed.

The queue changes proposal selection only. It cannot apply patches, execute generated code, promote a skill, merge a branch, or alter a protected administrator task.

## Capability-scoped proposal lease

Each queued proposal step receives a short-lived lease scoped to its queue index and worker cycle. A live lease denies a duplicate claim; an expired lease may be reclaimed after crash recovery. Lease identity includes a random stdlib nonce and is stored only as a digest. The lease controls proposal dispatch only and never grants permission to modify protected tasks, promote code, or execute model output.

Lease state transitions are explicit in durable state: `claimed` before dispatch, `released` after a backend result, and `exhausted` when no queue step remains. These states are audit markers, not authorization grants. A lease never enables patch application, generated-code execution, promotion, branch merge, or protected administrator mutation.

## Fresh-session handoff

After every bounded cycle, the worker atomically writes `.noesis_autoloop/handoff.json`. The manifest records the source cycle, result digest, one safe next action, an allowlist for code/tests/docs/private GitHub work, and a denylist for protected mutations, promotion, generated-code execution, and credential changes. It contains no command, endpoint, prompt, or secret text. A fresh scheduled task can read this manifest before selecting its next increment; it is a handoff contract, not proof of continuous agent-session execution.

Fresh sessions must validate `.noesis_autoloop/handoff.json` against the exact `noesis.autoloop-handoff.v1` schema before consuming it. Unknown fields, invalid cycle numbers, malformed result digests, or non-list policy fields fail closed as `handoff_*` errors; no inferred fallback action is permitted.
