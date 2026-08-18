# NOESIS UI Contract v1

Status: **implemented; P0-01/P0-02/P0-03 verified locally**

Version: `1.0`

## Purpose

This contract is the stable boundary between the NOESIS kernel and optional browser, desktop, Hermes WebUI and DeepSeek Harness adapters. The contract is data-only. It does not expose provider credentials, execute model-generated code or imply that a remote runtime has local workspace access.

## Common envelope

Every response uses the following fields:

```json
{
  "contract_version": "1.0",
  "ok": true,
  "status": "ready",
  "request_id": "random-id",
  "data": {},
  "error": null,
  "capabilities": {},
  "unavailable_reasons": []
}
```

`status` may be `ready`, `degraded`, `unavailable`, `denied`, `invalid_request` or `upstream_error`. A failed response has `ok=false` and a structured `error` object. A successful response has `ok=true` and no error. Request IDs are opaque correlation values and must not contain secrets.

Secret-shaped keys such as `token`, `secret`, `password`, `credential`, `authorization`, `api_key` and `private_key` are redacted recursively before JSON serialization. The UI receives capability metadata and model identifiers, never provider keys or authorization headers.

## `GET /health`

The read-only health response contains:

```json
{
  "contract_version": "1.0",
  "ok": true,
  "status": "degraded",
  "data": {
    "runtime_version": "0.1.0",
    "readiness": "ready",
    "binding": "127.0.0.1:0"
  },
  "capabilities": {
    "ui_contract": "ready",
    "provider_registry": "unavailable",
    "hermes_adapter": "unavailable",
    "deepseek_adapter": "unavailable",
    "hardened_sandbox": "unavailable"
  },
  "unavailable_reasons": [
    "provider_registry_unavailable",
    "hermes_adapter_unavailable",
    "deepseek_adapter_unavailable",
    "hardened_sandbox_unavailable"
  ]
}
```

`readiness=ready` means the local NOESIS control-plane process is alive. `status=degraded` means optional capabilities are absent. This distinction prevents a missing Hermes/DeepSeek adapter or hardened sandbox from being confused with a dead server.

The first implementation binds to `127.0.0.1` and supports a random port. Non-loopback binding requires a separate explicit adapter with authentication and warning policy. The endpoint is read-only and does not accept model prompts or tool commands.

## `GET /models` data shape

The provider registry returns model metadata only:

```json
{
  "models": [
    {
      "id": "local-model",
      "provider": "ollama",
      "endpoint_kind": "openai-compatible",
      "status": "ready",
      "capabilities": {
        "tools": false,
        "vision": false,
        "structured_output": true,
        "reasoning": false
      }
    }
  ]
}
```

A missing or incompatible provider returns `status=unavailable` with an empty model list and a reason. Provider URLs, API keys and authorization headers are not part of this response schema.

## P0-06 launch examples

From the repository root, run the metadata-only local control plane:

```text
python examples/run_control_plane.py --host 127.0.0.1 --port 8765
```

The server listens only on loopback by default. In a second terminal, the following commands are read-only and do not send provider credentials:

**Windows PowerShell**

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8765/health -Method Get | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri http://127.0.0.1:8765/models -Method Get | ConvertTo-Json -Depth 10
```

**Windows `curl.exe`**

```text
curl.exe http://127.0.0.1:8765/health
curl.exe http://127.0.0.1:8765/models
```

**macOS/Linux**

```text
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/models
```

To verify fail-soft behavior with no configured provider models, start with:

```text
python examples/run_control_plane.py --host 127.0.0.1 --port 8765 --empty-registry
```

The examples use only declarative demo metadata. They do not start Hermes, DeepSeek, Ollama, LM Studio or any model process.

## Telemetry dashboard endpoints

The read-only operator dashboard exposes three local telemetry routes:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/telemetry` | `GET` | Redacted snapshot of SSE streams, child runtimes and counters. |
| `/api/child-runtimes` | `GET` | Redacted child-runtime subset. |
| `/api/telemetry/events` | `GET` | One bounded `event: telemetry` SSE snapshot; clients reconnect for refresh. |

Telemetry is recursively redacted for secret-shaped keys and cannot invoke tools, providers or commands. `HealthServer.set_telemetry()` replaces the snapshot atomically. The dashboard is loopback-only by default and inherits existing authentication and non-loopback warning gates. A telemetry snapshot is not proof of native sandbox isolation or external provider execution.

## Adapter boundary

Hermes WebUI and DeepSeek Harness are optional child-runtime adapters. The UI contract normalizes their model/profile/session metadata, but it does not merge their private memory implicitly. Tool execution remains in the selected runtime workspace and its location is recorded as capability metadata. Remote runtime access must never be described as local hands.

## Contract tests

The contract is tested for deterministic serialization, secret redaction, valid/invalid statuses, required model fields, unsupported contract versions and fail-soft unavailable responses. P0-02 adds HTTP tests for loopback binding, read-only methods, unknown paths, bounded requests and clean shutdown. P0-03 adds provider registry fixtures for Ollama, LM Studio, llama.cpp, vLLM and OpenAI-compatible endpoints, plus `/models` HTTP tests for ready metadata and explicit unavailable state.
