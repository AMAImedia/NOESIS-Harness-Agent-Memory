"""Small read-only stdlib HTTP health endpoint for the NOESIS control plane."""
from __future__ import annotations

import hmac
import json
from dataclasses import asdict, is_dataclass
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping, Optional, Sequence, Tuple

from .provider_registry import ProviderRegistry
from .ui_assets import CONTROL_PLANE_HTML
from .session_stream import SessionEventBuffer, StreamContractError
from .task_session_api import TaskSessionError, TaskSessionStore
from .ui_contract import UIEnvelope, failure, health_payload, success


class _HealthHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class HealthServer:
    """Serve only GET /health and /; no model/tool execution is performed."""

    def __init__(self, *, runtime_version: str = "0.1.0", capabilities: Optional[Mapping[str, str]] = None, unavailable_reasons: Sequence[str] = (), provider_registry: Optional[ProviderRegistry] = None, host: str = "127.0.0.1", port: int = 0, max_request_bytes: int = 4096, allow_non_loopback: bool = False, auth_token: Optional[str] = None, acknowledge_lan_warning: bool = False, session_store: Optional[TaskSessionStore] = None):
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
        self.session_store = session_store
        self._stream_buffers: dict[str, SessionEventBuffer] = {}
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

            def _body(self) -> Mapping[str, Any]:
                length = int(self.headers.get("Content-Length", "0") or "0")
                if length < 0 or length > parent.max_request_bytes:
                    raise TaskSessionError("request_body_too_large")
                raw = self.rfile.read(length) if length else b"{}"
                if len(raw) > parent.max_request_bytes:
                    raise TaskSessionError("request_body_too_large")
                try:
                    value = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise TaskSessionError("invalid_json") from exc
                if not isinstance(value, Mapping):
                    raise TaskSessionError("request_object_required")
                return value

            @staticmethod
            def _jsonable(value: Any) -> Any:
                if is_dataclass(value):
                    return Handler._jsonable(asdict(value))
                if isinstance(value, Mapping):
                    return {str(key): Handler._jsonable(item) for key, item in value.items()}
                if isinstance(value, (list, tuple)):
                    return [Handler._jsonable(item) for item in value]
                return value

            def _session_buffer(self, session_id: str) -> SessionEventBuffer:
                if session_id not in parent._stream_buffers:
                    parent._stream_buffers[session_id] = SessionEventBuffer(session_id)
                return parent._stream_buffers[session_id]

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
                elif self.path.startswith("/api/tasks/") and parent.session_store is not None:
                    task_id = self.path[len("/api/tasks/"):].rstrip("/")
                    try:
                        self._send(success({"task": self._jsonable(parent.session_store.task(task_id))}), 200)
                    except TaskSessionError as exc:
                        self._send(failure("invalid_request", "task_unavailable", str(exc)), 404)
                elif self.path.startswith("/api/sessions/") and parent.session_store is not None:
                    suffix = self.path[len("/api/sessions/"):]
                    if suffix.endswith("/events"):
                        session_id = suffix[:-len("/events")].rstrip("/")
                        last_id = int(self.headers.get("Last-Event-ID", "0") or "0")
                        body = self._session_buffer(session_id).sse_since(last_id).encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                        self.send_header("Cache-Control", "no-store")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                    else:
                        try:
                            self._send(success(self._jsonable(parent.session_store.resume(suffix))), 200)
                        except TaskSessionError as exc:
                            self._send(failure("invalid_request", "session_unavailable", str(exc)), 404)
                else:
                    self._send(failure("invalid_request", "not_found", "unsupported route or session API unavailable"), 404)

            def do_POST(self) -> None:  # noqa: N802
                if not self._authorized():
                    self._send_unauthorized()
                    return
                if parent.session_store is None:
                    self._send(failure("denied", "read_only", "session API is not enabled"), 405)
                    return
                try:
                    payload = self._body()
                    if self.path == "/api/sessions":
                        record = parent.session_store.create_session(str(payload.get("owner", "")), session_id=payload.get("session_id"))
                        self._session_buffer(record.session_id).publish("session_started", {"state": record.state})
                        self._send(success({"session": self._jsonable(record)}), 201)
                        return
                    if self.path == "/api/commands":
                        command = parent.session_store.dispatch(payload)
                        result = command.get("result")
                        if hasattr(result, "session_id"):
                            session_id = result.session_id
                            task_id = None
                        elif hasattr(result, "task_id"):
                            session_id = result.session_id
                            task_id = result.task_id
                        else:
                            session_id = str(result.get("session_id", "")) if isinstance(result, Mapping) else ""
                            task_id = None
                        if not session_id:
                            raise TaskSessionError("command_session_id_required")
                        event = self._session_buffer(session_id).publish("command", {"command_id": command["command_id"], "command": command["command"], "result": self._jsonable(result)}, task_id=task_id)
                        self._send(success({"command": self._jsonable(command), "sequence": event.sequence}), 202)
                        return
                    prefix = "/api/sessions/"
                    if self.path.startswith(prefix) and self.path.endswith("/messages"):
                        session_id = self.path[len(prefix):-len("/messages")].rstrip("/")
                        event_id = parent.session_store.append_message(session_id, str(payload.get("role", "user")), str(payload.get("content", "")), command_id=payload.get("command_id"))
                        event = self._session_buffer(session_id).publish("message", {"role": str(payload.get("role", "user")), "event_id": event_id, "content": str(payload.get("content", ""))})
                        self._send(success({"event_id": event_id, "sequence": event.sequence}), 201)
                        return
                except (TaskSessionError, StreamContractError, ValueError) as exc:
                    self._send(failure("invalid_request", "session_command_rejected", str(exc)), 400)
                    return
                self._send(failure("invalid_request", "not_found", "unsupported session command"), 404)

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
