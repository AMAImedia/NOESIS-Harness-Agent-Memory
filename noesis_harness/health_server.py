"""Small read-only stdlib HTTP health endpoint for the NOESIS control plane."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping, Sequence, Tuple

from .provider_registry import ProviderRegistry
from .ui_contract import UIEnvelope, failure, health_payload


class _HealthHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class HealthServer:
    """Serve only GET /health and /; no model/tool execution is performed."""

    def __init__(self, *, runtime_version: str = "0.1.0", capabilities: Mapping[str, str] | None = None, unavailable_reasons: Sequence[str] = (), provider_registry: ProviderRegistry | None = None, host: str = "127.0.0.1", port: int = 0, max_request_bytes: int = 4096):
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("health server defaults to loopback; non-loopback requires an explicit external adapter")
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
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/health":
                    self._send(parent.envelope(), 200)
                elif self.path == "/models":
                    self._send(parent.models_envelope(), 200)
                elif self.path == "/":
                    self._send(parent.envelope(), 200)
                else:
                    self._send(failure("invalid_request", "not_found", "only GET /health and /models are supported"), 404)

            def do_POST(self) -> None:  # noqa: N802
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
