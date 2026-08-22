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
