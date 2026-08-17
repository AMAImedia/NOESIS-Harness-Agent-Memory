"""Small read-only stdlib HTTP health endpoint for the NOESIS control plane."""
from __future__ import annotations

import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping, Optional, Sequence, Tuple

from .provider_registry import ProviderRegistry
from .ui_assets import CONTROL_PLANE_HTML
from .ui_contract import UIEnvelope, failure, health_payload


class _HealthHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class HealthServer:
    """Serve only GET /health and /; no model/tool execution is performed."""

    def __init__(self, *, runtime_version: str = "0.1.0", capabilities: Optional[Mapping[str, str]] = None, unavailable_reasons: Sequence[str] = (), provider_registry: Optional[ProviderRegistry] = None, host: str = "127.0.0.1", port: int = 0, max_request_bytes: int = 4096, allow_non_loopback: bool = False, auth_token: Optional[str] = None, acknowledge_lan_warning: bool = False):
        loopback = host in {"127.0.0.1", "localhost", "::1"}
        if not loopback and not allow_non_loopback:
            raise ValueError("health server defaults to loopback; non-loopback requires allow_non_loopback=True")
        if not loopback and (not auth_token or len(str(auth_token)) < 16):
            raise ValueError("non-loopback adapter requires an auth token of at least 16 characters")
        if not loopback and not acknowledge_lan_warning:
            raise ValueError("non-loopback adapter requires explicit LAN warning acknowledgement")
        if not (0 <= int(port) <= 65535):
            raise ValueError("port must be in 0..65535")
        if not (256 <= int(max_request_bytes) <= 1_048_576):
            raise ValueError("max_request_bytes must be between 256 and 1048576")
        self.runtime_version = str(runtime_version)
        self.capabilities = dict(capabilities or {"ui_contract": "ready", "provider_registry": "unavailable", "hermes_adapter": "unavailable", "deepseek_adapter": "unavailable", "hardened_sandbox": "unavailable"})
        self.unavailable_reasons = tuple(str(item) for item in unavailable_reasons) or tuple(f"{key}_unavailable" for key, value in self.capabilities.items() if value == "unavailable")
        self.provider_registry = provider_registry or ProviderRegistry()
        self.host = host
        self.port = int(port)
        self.max_request_bytes = int(max_request_bytes)
        self.allow_non_loopback = bool(allow_non_loopback)
        self._auth_token = str(auth_token) if auth_token else None
        self.lan_warning = "authenticated non-loopback adapter; do not expose to untrusted networks" if not loopback else "loopback-only"
        self._server: _HealthHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def envelope(self) -> UIEnvelope:
        return health_payload(runtime_version=self.runtime_version, readiness="ready", binding=f"{self.host}:{self.bound_port}", capabilities=self.capabilities, unavailable_reasons=self.unavailable_reasons)

    def models_envelope(self) -> UIEnvelope:
        return self.provider_registry.envelope()

    @property
    def bound_port(self) -> int:
        return int(self._server.server_address[1]) if self._server is not None else self.port

    @property
    def address(self) -> Tuple[str, int]:
        return self.host, self.bound_port

    def _handler(self):
        parent = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "NOESISHealth/1"
            protocol_version = "HTTP/1.1"

            def _send_html(self, body: str, code: int = 200) -> None:
                payload = body.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-NOESIS-Network-Warning", parent.lan_warning)
                self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'")
                self.end_headers()
                self.wfile.write(payload)

            def _send(self, envelope: UIEnvelope, code: int = 200) -> None:
                body = envelope.to_json().encode("utf-8")
                if len(body) > parent.max_request_bytes * 4:
                    envelope = failure("upstream_error", "response_too_large", "health response exceeds configured bound")
                    body = envelope.to_json().encode("utf-8")
                    code = 500
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-NOESIS-Network-Warning", parent.lan_warning)
                self.end_headers()
                self.wfile.write(body)

            def _authorized(self) -> bool:
                if parent._auth_token is None:
                    return True
                supplied = self.headers.get("Authorization", "")
                expected = "Bearer " + parent._auth_token
                return hmac.compare_digest(supplied, expected)

            def _send_unauthorized(self) -> None:
                self._send(failure("denied", "authentication_required", "valid bearer authentication is required"), 401)

            def do_GET(self) -> None:  # noqa: N802
                if not self._authorized():
                    self._send_unauthorized()
                    return
                if self.path == "/health":
                    self._send(parent.envelope(), 200)
                elif self.path == "/models":
                    self._send(parent.models_envelope(), 200)
                elif self.path in {"/", "/ui"}:
                    self._send_html(CONTROL_PLANE_HTML, 200)
                else:
                    self._send(failure("invalid_request", "not_found", "only GET /, /ui, /health and /models are supported"), 404)

            def do_POST(self) -> None:  # noqa: N802
                if not self._authorized():
                    self._send_unauthorized()
                    return
                self._send(failure("denied", "read_only", "health endpoint is read-only"), 405)

            def log_message(self, *_args: Any) -> None:
                return

        return Handler

    def start(self) -> Tuple[str, int]:
        if self._server is not None:
            return self.address
        self._server = _HealthHTTPServer((self.host, self.port), self._handler())
        self.port = int(self._server.server_address[1])
        self._thread = threading.Thread(target=self._server.serve_forever, name="noesis-health", daemon=True)
        self._thread.start()
        return self.address

    def stop(self) -> None:
        server, thread = self._server, self._thread
        self._server = None
        self._thread = None
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)

    def __enter__(self) -> "HealthServer":
        self.start()
        return self

    def __exit__(self, *_args: Any) -> None:
        self.stop()


__all__ = ["HealthServer"]
