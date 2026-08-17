"""Explicit provider invocation adapters for DeepSeek/Hermes-compatible APIs.

The adapter is deliberately separate from provider metadata discovery. It only
contacts a provider when ``invoke`` is called explicitly by an approved task.
Returned model text is data; this module never executes it.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Sequence
from urllib.parse import urljoin

from .provider_registry import CAPABILITY_KEYS

MAX_REQUEST_BYTES = 256 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class ProviderInvocationError(RuntimeError):
    """Raised when an explicit provider invocation cannot be completed."""


@dataclass(frozen=True)
class InvocationRequest:
    session_id: str
    task_id: str
    model: str
    messages: tuple[Mapping[str, Any], ...]
    required_capabilities: tuple[str, ...] = ()
    tools: tuple[Mapping[str, Any], ...] = ()
    stream: bool = False


@dataclass(frozen=True)
class InvocationResponse:
    status: str
    provider_id: str
    model: str
    request_id: str
    output: Mapping[str, Any]
    latency_ms: float
    reason: str = ""


class OpenAICompatibleInvocationAdapter:
    """Call a pinned OpenAI-compatible endpoint under explicit capability policy."""

    def __init__(
        self,
        provider_id: str,
        base_url: str,
        model: str,
        capabilities: Mapping[str, bool],
        *,
        auth_mode: str = "none",
        credential_ref: Optional[str] = None,
        credential_resolver: Optional[Callable[[str], str]] = None,
        timeout_seconds: float = 30.0,
        transport: Optional[Callable[[urllib.request.Request, float], tuple[int, bytes]]] = None,
    ):
        if not provider_id or not model or not base_url.startswith(("http://", "https://")):
            raise ProviderInvocationError("provider_id, model and absolute HTTP base_url are required")
        if auth_mode not in {"none", "bearer_ref", "bridge_managed"}:
            raise ProviderInvocationError("unsupported auth_mode")
        if auth_mode == "bearer_ref" and (not credential_ref or not credential_ref.isidentifier()):
            raise ProviderInvocationError("bearer_ref requires identifier-only credential_ref")
        if auth_mode == "bearer_ref" and credential_resolver is None:
            raise ProviderInvocationError("credential_resolver required for bearer_ref")
        if timeout_seconds <= 0:
            raise ProviderInvocationError("timeout_seconds must be positive")
        unknown = sorted(set(capabilities) - CAPABILITY_KEYS)
        if unknown:
            raise ProviderInvocationError("unknown capability: %s" % unknown[0])
        self.provider_id = provider_id
        self.base_url = base_url.rstrip("/") + "/"
        self.model = model
        self.capabilities = {key: bool(value) for key, value in capabilities.items()}
        self.auth_mode = auth_mode
        self.credential_ref = credential_ref
        self.credential_resolver = credential_resolver
        self.timeout_seconds = timeout_seconds
        self._transport = transport or self._default_transport

    @staticmethod
    def _default_transport(request: urllib.request.Request, timeout: float) -> tuple[int, bytes]:
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                return int(response.status), body
        except urllib.error.HTTPError as exc:
            body = exc.read(MAX_RESPONSE_BYTES + 1)
            return int(exc.code), body
        except (OSError, urllib.error.URLError) as exc:
            raise ProviderInvocationError("provider_unreachable:%s" % type(exc).__name__) from exc

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.auth_mode == "bearer_ref":
            assert self.credential_resolver is not None
            token = self.credential_resolver(self.credential_ref or "")
            if not token or any(char in token for char in "\r\n"):
                raise ProviderInvocationError("credential_resolver returned invalid token")
            headers["Authorization"] = "Bearer " + token
        return headers

    def _validate_request(self, request: InvocationRequest) -> None:
        if not request.session_id or not request.task_id or not request.model:
            raise ProviderInvocationError("session_id, task_id and model are required")
        if request.model != self.model:
            raise ProviderInvocationError("model_not_pinned")
        unknown = sorted(set(request.required_capabilities) - CAPABILITY_KEYS)
        if unknown:
            raise ProviderInvocationError("unknown required capability: %s" % unknown[0])
        missing = sorted(capability for capability in request.required_capabilities if not self.capabilities.get(capability, False))
        if missing:
            raise ProviderInvocationError("capability_not_granted:%s" % missing[0])
        if request.tools and not self.capabilities.get("tools", False):
            raise ProviderInvocationError("capability_not_granted:tools")
        if request.stream and not self.capabilities.get("streaming", False):
            raise ProviderInvocationError("capability_not_granted:streaming")
        if not request.messages:
            raise ProviderInvocationError("messages are required")

    def invoke(self, request: InvocationRequest) -> InvocationResponse:
        """Perform one explicit request; provider output is returned as data only."""
        self._validate_request(request)
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [dict(message) for message in request.messages],
            "stream": bool(request.stream),
        }
        if request.tools:
            payload["tools"] = [dict(tool) for tool in request.tools]
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > MAX_REQUEST_BYTES:
            raise ProviderInvocationError("request_exceeds_bounded_payload")
        request_obj = urllib.request.Request(urljoin(self.base_url, "v1/chat/completions"), data=encoded, method="POST", headers=self._headers())
        started = time.perf_counter()
        status, body = self._transport(request_obj, self.timeout_seconds)
        latency_ms = (time.perf_counter() - started) * 1000.0
        if len(body) > MAX_RESPONSE_BYTES:
            raise ProviderInvocationError("response_exceeds_bounded_payload")
        try:
            decoded = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderInvocationError("provider_invalid_json") from exc
        if status < 200 or status >= 300:
            return InvocationResponse("unavailable", self.provider_id, request.model, "", {"error": decoded if isinstance(decoded, Mapping) else {"detail": "provider_error"}}, latency_ms, "provider_http_%d" % status)
        if not isinstance(decoded, Mapping):
            raise ProviderInvocationError("provider_response_must_be_object")
        request_id = str(decoded.get("id", ""))
        return InvocationResponse("ready", self.provider_id, request.model, request_id, dict(decoded), latency_ms, "explicit_invocation")


__all__ = ["MAX_REQUEST_BYTES", "MAX_RESPONSE_BYTES", "InvocationRequest", "InvocationResponse", "OpenAICompatibleInvocationAdapter", "ProviderInvocationError"]
