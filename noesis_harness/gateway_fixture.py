"""Deterministic local Hermes/DeepSeek gateway fixtures for integration tests.

Patterns are borrowed from NOESIS HealthServer auth boundaries, BridgeDiscovery
read-only probes, and append-only audit logs. Fixtures are test-only runtime
surfaces: they expose health/model metadata, never execute model/tool output,
and keep request audit records free of credentials and cross-agent payloads.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Mapping, Optional, Tuple


class GatewayFixtureError(ValueError):
    """Raised when a fixture configuration is unsafe or invalid."""


class GatewayFixture:
    """Run a local metadata-only gateway fixture in a background thread."""

    def __init__(self, kind: str, *, token: Optional[str] = None, models: Tuple[Mapping[str, object], ...] = (), audit_path: Optional[str] = None):
        if kind not in {"hermes_webui", "deepseek_harness"}:
            raise GatewayFixtureError("unsupported fixture kind")
        if token is not None and len(token) < 16:
            raise GatewayFixtureError("fixture token must be at least 16 characters")
        self.kind = kind
        self.token = token
        self.models = tuple(dict(model) for model in models)
        self.audit_path = Path(audit_path).expanduser().resolve() if audit_path else None
        self._server = None
        self._thread = None

    @property
    def address(self) -> Tuple[str, int]:
        if self._server is None:
            raise GatewayFixtureError("fixture is not started")
        return self._server.server_address[0], int(self._server.server_address[1])

    def _audit(self, event: Mapping[str, object]) -> None:
        if self.audit_path is None:
            return
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(event)
        payload["timestamp"] = time.time()
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def start(self) -> "GatewayFixture":
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                auth = self.headers.get("Authorization", "")
                authorized = fixture.token is None or auth == "Bearer " + fixture.token
                if not authorized:
                    fixture._audit({"kind": fixture.kind, "path": self.path, "status": 401, "agent_id": self.headers.get("X-NOESIS-Agent", "unknown")})
                    self.send_response(401)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"status":"unavailable","reason":"authentication_required"}')
                    return
                if self.path == "/health":
                    payload = {"contract_version": "1.0", "status": "ready", "capabilities": {fixture.kind: "ready"}}
                elif self.path == "/models":
                    payload = {"contract_version": "1.0", "status": "ready", "data": {"models": list(fixture.models)}}
                else:
                    self.send_response(404)
                    self.end_headers()
                    return
                fixture._audit({"kind": fixture.kind, "path": self.path, "status": 200, "agent_id": self.headers.get("X-NOESIS-Agent", "unknown")})
                body = json.dumps(payload, sort_keys=True).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format, *_args):
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, name="noesis-gateway-fixture", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def __enter__(self) -> "GatewayFixture":
        return self.start()

    def __exit__(self, *_args: object) -> None:
        self.stop()

    def audit_events(self):
        if self.audit_path is None or not self.audit_path.is_file():
            return ()
        return tuple(json.loads(line) for line in self.audit_path.read_text(encoding="utf-8").splitlines() if line.strip())


__all__ = ["GatewayFixture", "GatewayFixtureError"]
