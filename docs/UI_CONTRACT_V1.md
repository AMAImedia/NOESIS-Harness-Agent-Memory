# NOESIS UI Contract v1

Status: **implemented as a stdlib contract module; endpoint integration is P0-02**

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

## Adapter boundary

Hermes WebUI and DeepSeek Harness are optional child-runtime adapters. The UI contract normalizes their model/profile/session metadata, but it does not merge their private memory implicitly. Tool execution remains in the selected runtime workspace and its location is recorded as capability metadata. Remote runtime access must never be described as local hands.

## Contract tests

The contract is tested for deterministic serialization, secret redaction, valid/invalid statuses, required model fields, unsupported contract versions and fail-soft unavailable responses. P0-02 adds HTTP tests for loopback binding, read-only methods, unknown paths, bounded requests and clean shutdown.
