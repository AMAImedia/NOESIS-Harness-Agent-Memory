"""Small read-only stdlib HTTP health endpoint for the NOESIS control plane."""
from __future__ import annotations

import hmac
import json
from dataclasses import asdict, is_dataclass
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple

from .provider_registry import ProviderRegistry
from .ui_assets import CONTROL_PLANE_HTML
from .session_stream import SessionEventBuffer, StreamContractError
from .task_session_api import TaskSessionError, TaskSessionStore
from .promotion_integration import OperatorAuthContext, OperatorSessionAction, PromotionApprovalAction
from .ui_contract import UIEnvelope, failure, health_payload, success


class _HealthHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class HealthServer:
    """Serve only GET /health and /; no model/tool execution is performed."""

    def __init__(self, *, runtime_version: str = "0.1.0", capabilities: Optional[Mapping[str, str]] = None, unavailable_reasons: Sequence[str] = (), provider_registry: Optional[ProviderRegistry] = None, host: str = "127.0.0.1", port: int = 0, max_request_bytes: int = 4096, allow_non_loopback: bool = False, auth_token: Optional[str] = None, acknowledge_lan_warning: bool = False, session_store: Optional[TaskSessionStore] = None, promotion_telemetry: Optional[Any] = None, promotion_action_handler: Optional[Callable[[PromotionApprovalAction, OperatorAuthContext], Mapping[str, Any]]] = None, operator_session_action_handler: Optional[Callable[[OperatorSessionAction, OperatorAuthContext], Mapping[str, Any]]] = None, administrative_policy_handler: Optional[Callable[[Mapping[str, Any], OperatorAuthContext], Mapping[str, Any]]] = None, migration_mode_change_handler: Optional[Callable[[Mapping[str, Any], OperatorAuthContext], Mapping[str, Any]]] = None, migration_mode_source: Optional[Any] = None, migration_audit_provider: Optional[Callable[[], Sequence[Mapping[str, Any]]]] = None, migration_readiness_provider: Optional[Callable[[], Mapping[str, Any]]] = None, operator_id: Optional[str] = None, operator_session_id: Optional[str] = None, operator_scopes: Sequence[str] = ()):
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
        self.promotion_telemetry = promotion_telemetry
        self.promotion_action_handler = promotion_action_handler
        self.operator_session_action_handler = operator_session_action_handler
        self.administrative_policy_handler = administrative_policy_handler
        self.migration_mode_change_handler = migration_mode_change_handler
        self.migration_mode_source = migration_mode_source
        self.migration_audit_provider = migration_audit_provider
        self.migration_readiness_provider = migration_readiness_provider
        self.operator_auth_context = OperatorAuthContext(str(operator_id), str(operator_session_id), tuple(str(item) for item in operator_scopes)) if operator_id and operator_session_id else None
        self._stream_buffers: dict[str, SessionEventBuffer] = {}
        self._telemetry_lock = threading.RLock()
        self._telemetry: dict[str, Any] = {
            "streams": [],
            "child_runtimes": [],
            "counters": {"events": 0, "active_streams": 0, "active_children": 0},
            "source": "local-control-plane",
            "updated_at_epoch": 0,
        }
        self.host = host
        self.port = int(port)
        self.max_request_bytes = int(max_request_bytes)
        self.allow_non_loopback = bool(allow_non_loopback)
        self._auth_token = str(auth_token) if auth_token else None
        self.lan_warning = "authenticated non-loopback adapter; do not expose to untrusted networks" if not loopback else "loopback-only"
        self._server: _HealthHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def _migration_readiness_snapshot(self) -> Mapping[str, Any]:
        if self.migration_readiness_provider is not None:
            try:
                value = self.migration_readiness_provider()
                if not isinstance(value, Mapping):
                    raise ValueError("migration_readiness_must_be_object")
                return self._redact_telemetry(dict(value))
            except Exception as exc:
                return {"schema_version": "noesis.migration-readiness.v1", "mode": "blocked", "blocked": True, "rollback_available": False, "status": "blocked", "reason": "readiness_provider_error:" + type(exc).__name__, "automatic_cutover": False}
        if self.migration_mode_source is not None and hasattr(self.migration_mode_source, "readiness"):
            try:
                return self._redact_telemetry(dict(self.migration_mode_source.readiness()))
            except Exception as exc:
                return {"schema_version": "noesis.migration-readiness.v1", "mode": "blocked", "blocked": True, "rollback_available": False, "status": "blocked", "reason": "mode_source_error:" + type(exc).__name__, "automatic_cutover": False}
        return {"schema_version": "noesis.migration-readiness.v1", "mode": "legacy", "blocked": False, "rollback_available": False, "status": "legacy", "automatic_cutover": False, "operator_owned": False}

    def _migration_audit_snapshot(self) -> tuple[Mapping[str, Any], ...]:
        provider = self.migration_audit_provider
        if provider is None and self.migration_mode_source is not None and hasattr(self.migration_mode_source, "mode_audit"):
            provider = self.migration_mode_source.mode_audit
        if provider is None:
            return ()
        try:
            records = provider()
            if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
                raise ValueError("migration_audit_must_be_sequence")
            return tuple(self._redact_telemetry(dict(item)) for item in records[:50] if isinstance(item, Mapping))
        except Exception as exc:
            return ({"status": "blocked", "reason": "migration_audit_provider_error:" + type(exc).__name__},)

    def envelope(self) -> UIEnvelope:
        readiness = self._migration_readiness_snapshot()
        return health_payload(runtime_version=self.runtime_version, readiness="unavailable" if readiness.get("blocked") else "ready", binding=f"{self.host}:{self.bound_port}", capabilities=self.capabilities, unavailable_reasons=self.unavailable_reasons + (("migration_readiness_blocked",) if readiness.get("blocked") else ()))

    def models_envelope(self) -> UIEnvelope:
        return self.provider_registry.envelope()

    def set_telemetry(self, *, streams: Sequence[Mapping[str, Any]] = (), child_runtimes: Sequence[Mapping[str, Any]] = (), counters: Optional[Mapping[str, Any]] = None) -> None:
        """Replace the redacted, read-only operator telemetry snapshot."""
        with self._telemetry_lock:
            safe_streams = [self._redact_telemetry(dict(item)) for item in streams]
            safe_children = [self._redact_telemetry(dict(item)) for item in child_runtimes]
            safe_counters = self._redact_telemetry(dict(counters or {}))
            safe_counters.setdefault("active_streams", len(safe_streams))
            safe_counters.setdefault("active_children", len(safe_children))
            self._telemetry = {
                "streams": safe_streams,
                "child_runtimes": safe_children,
                "counters": safe_counters,
                "source": "local-control-plane",
                "updated_at_epoch": int(time.time()),
            }

    @staticmethod
    def _redact_telemetry(value: Any) -> Any:
        secret_names = ("token", "secret", "password", "credential", "authorization", "api_key", "private_key")
        if isinstance(value, Mapping):
            return {str(key): ("[REDACTED]" if any(name in str(key).casefold() for name in secret_names) else HealthServer._redact_telemetry(item)) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [HealthServer._redact_telemetry(item) for item in value]
        return value

    def telemetry_snapshot(self) -> Mapping[str, Any]:
        with self._telemetry_lock:
            snapshot = self._redact_telemetry(self._telemetry)
        snapshot = dict(snapshot)
        snapshot["migration_readiness"] = self._migration_readiness_snapshot()
        snapshot["migration_audit"] = self._migration_audit_snapshot()
        if self.promotion_telemetry is not None and hasattr(self.promotion_telemetry, "snapshot"):
            snapshot["learning_promotion"] = self._redact_telemetry(self.promotion_telemetry.snapshot())
        return snapshot

    def operator_snapshot(self) -> Mapping[str, Any]:
        """Return a bounded, read-only operator view with no execution side effects."""
        context = self.operator_auth_context
        return {
            "schema_version": "noesis.operator-snapshot.v1",
            "health": self.envelope().to_dict(),
            "models": self.models_envelope().to_dict(),
            "telemetry": self.telemetry_snapshot(),
            "operator_context": {
                "configured": context is not None,
                "operator_id": context.operator_id if context is not None else "",
                "session_id": context.session_id if context is not None else "",
                "scopes": list(context.scopes) if context is not None else [],
            },
            "execution_claim": "read_only_snapshot",
        }

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
                elif self.path == "/api/readiness":
                    self._send(success({"migration_readiness": parent._migration_readiness_snapshot()}), 200)
                elif self.path == "/api/operator/snapshot":
                    self._send(success(parent.operator_snapshot()), 200)
                elif self.path in {"/api/telemetry", "/api/child-runtimes"}:
                    snapshot = parent.telemetry_snapshot()
                    if self.path == "/api/child-runtimes":
                        snapshot = {"child_runtimes": snapshot["child_runtimes"], "counters": snapshot["counters"], "updated_at_epoch": snapshot["updated_at_epoch"]}
                    self._send(success({"telemetry": snapshot}), 200)
                elif self.path == "/api/audit/migration":
                    self._send(success({"migration_audit": parent._migration_audit_snapshot()}), 200)
                elif self.path == "/api/telemetry/events":
                    payload = success({"telemetry": parent.telemetry_snapshot()}).to_json()
                    body = ("event: telemetry\ndata: " + payload + "\n\n").encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
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
                try:
                    payload = self._body()
                    if self.path == "/api/operator-sessions":
                        if parent.operator_session_action_handler is None:
                            self._send(failure("denied", "operator_session_actions_unavailable", "operator session action handler is not enabled"), 405)
                            return
                        if parent.operator_auth_context is None:
                            self._send(failure("denied", "operator_context_unavailable", "operator session context is not configured"), 403)
                            return
                        action = OperatorSessionAction.from_mapping(payload)
                        result = parent.operator_session_action_handler(action, parent.operator_auth_context)
                        if not isinstance(result, Mapping):
                            raise TaskSessionError("operator_session_action_handler_must_return_object")
                        self._send(success({"action": action.to_mapping(), "result": dict(result)}), 202)
                        return
                    if self.path == "/api/admin/migration-mode":
                        if parent.migration_mode_change_handler is None:
                            self._send(failure("denied", "migration_mode_actions_unavailable", "migration mode action handler is not enabled"), 405)
                            return
                        if parent.operator_auth_context is None:
                            self._send(failure("denied", "operator_context_unavailable", "operator session context is not configured"), 403)
                            return
                        if payload.get("schema_version") != "noesis.migration-mode-action.v1":
                            raise ValueError("unsupported_migration_mode_action")
                        result = parent.migration_mode_change_handler(dict(payload), parent.operator_auth_context)
                        if not isinstance(result, Mapping):
                            raise TaskSessionError("migration_mode_handler_must_return_object")
                        self._send(success({"action": {"schema_version": payload.get("schema_version"), "action": payload.get("action"), "mode": payload.get("mode")}, "result": dict(result)}), 202)
                        return
                    if self.path == "/api/admin/reviewer-policy":
                        if parent.administrative_policy_handler is None:
                            self._send(failure("denied", "administrative_policy_unavailable", "administrative policy handler is not enabled"), 405)
                            return
                        if parent.operator_auth_context is None:
                            self._send(failure("denied", "operator_context_unavailable", "operator session context is not configured"), 403)
                            return
                        if payload.get("schema_version") != "noesis.administrative-policy.v1" or payload.get("action") not in {"grant_reviewer", "revoke_reviewer"}:
                            raise ValueError("unsupported_administrative_policy_action")
                        result = parent.administrative_policy_handler(dict(payload), parent.operator_auth_context)
                        if not isinstance(result, Mapping):
                            raise TaskSessionError("administrative_policy_handler_must_return_object")
                        self._send(success({"action": {"schema_version": payload.get("schema_version"), "action": payload.get("action")}, "result": dict(result)}), 202)
                        return
                    if self.path == "/api/promotion-actions":
                        if parent.promotion_action_handler is None:
                            self._send(failure("denied", "promotion_actions_unavailable", "promotion action handler is not enabled"), 405)
                            return
                        if parent.operator_auth_context is None:
                            self._send(failure("denied", "operator_context_unavailable", "operator session context is not configured"), 403)
                            return
                        action = PromotionApprovalAction.from_mapping(payload)
                        result = parent.promotion_action_handler(action, parent.operator_auth_context)
                        if not isinstance(result, Mapping):
                            raise TaskSessionError("promotion_action_handler_must_return_object")
                        self._send(success({"action": action.to_mapping(), "result": dict(result)}), 202)
                        return
                    if parent.session_store is None:
                        self._send(failure("denied", "read_only", "session API is not enabled"), 405)
                        return
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
        self._migration_readiness_snapshot()
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
