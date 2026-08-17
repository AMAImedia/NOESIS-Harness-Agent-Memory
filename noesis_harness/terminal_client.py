"""Stdlib terminal client for the NOESIS versioned local session API."""

from __future__ import annotations

import argparse
import json
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Optional


class TerminalClientError(RuntimeError):
    """Raised for bounded client or API failures."""


@dataclass(frozen=True)
class SessionClient:
    base_url: str
    auth_token: Optional[str] = None
    timeout_seconds: float = 10.0

    def _request(self, path: str, method: str = "GET", payload: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        data = None if payload is None else json.dumps(dict(payload), ensure_ascii=False).encode("utf-8")
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if self.auth_token:
            headers["Authorization"] = "Bearer " + self.auth_token
        request = urllib.request.Request(self.base_url.rstrip("/") + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read()
        except Exception as exc:
            raise TerminalClientError("request_failed:%s" % type(exc).__name__) from exc
        try:
            value = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TerminalClientError("invalid_json_response") from exc
        if not isinstance(value, Mapping):
            raise TerminalClientError("response_object_required")
        return value

    def create(self, owner: str) -> Mapping[str, Any]:
        return self._request("/api/sessions", "POST", {"owner": owner})

    def resume(self, session_id: str) -> Mapping[str, Any]:
        return self._request("/api/sessions/" + session_id)

    def send(self, session_id: str, content: str, role: str = "user") -> Mapping[str, Any]:
        return self._request("/api/sessions/" + session_id + "/messages", "POST", {"role": role, "content": content})


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="NOESIS local session terminal client")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--owner", default="local-user")
    parser.add_argument("--session-id")
    parser.add_argument("--message")
    args = parser.parse_args(argv)
    client = SessionClient(args.base_url)
    result = client.create(args.owner) if not args.session_id else client.resume(args.session_id)
    session_id = result.get("data", {}).get("session", {}).get("session_id") or args.session_id
    if args.message and session_id:
        result = client.send(session_id, args.message)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


__all__ = ["SessionClient", "TerminalClientError", "main"]
