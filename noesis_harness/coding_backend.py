"""Bounded coding-backend adapters.

The core is stdlib-only and fail-closed. Process execution and local HTTP
inference are separate adapters; neither imports or executes model-generated
code in the parent process.
"""
from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class BackendResult:
    status: str
    returncode: Optional[int]
    stdout: str
    stderr: str
    command_digest: str
    reason: str


class CodingBackendError(ValueError):
    pass


class BoundedCodingBackend:
    def __init__(self, argv: Sequence[str], worktree: Path, timeout_seconds: float = 900.0, output_limit: int = 200000):
        if not argv or not all(isinstance(item, str) and item for item in argv):
            raise CodingBackendError("explicit_argv_required")
        self.argv = tuple(argv)
        self.worktree = Path(worktree).resolve()
        if not self.worktree.is_dir():
            raise CodingBackendError("worktree_missing")
        if timeout_seconds <= 0 or output_limit <= 0:
            raise CodingBackendError("positive_limits_required")
        self.timeout_seconds = float(timeout_seconds)
        self.output_limit = int(output_limit)

    @staticmethod
    def command_digest(argv: Sequence[str]) -> str:
        return hashlib.sha256("\0".join(argv).encode("utf-8")).hexdigest()

    def _bounded(self, value: bytes) -> str:
        text = value.decode("utf-8", errors="replace")
        return text[: self.output_limit]

    def _terminate(self, process: subprocess.Popen) -> None:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except (OSError, ProcessLookupError):
                process.kill()

    def run(self) -> BackendResult:
        digest = self.command_digest(self.argv)
        try:
            process = subprocess.Popen(
                self.argv,
                cwd=str(self.worktree),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=(os.name != "nt"),
                creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0),
            )
        except (OSError, ValueError) as exc:
            return BackendResult("spawn_error", None, "", "", digest, type(exc).__name__)
        try:
            stdout, stderr = process.communicate(timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            self._terminate(process)
            stdout, stderr = process.communicate()
            return BackendResult("timeout", None, self._bounded(stdout or exc.output or b""), self._bounded(stderr or exc.stderr or b""), digest, "process_timeout")
        status = "passed" if process.returncode == 0 else "failed"
        return BackendResult(status, process.returncode, self._bounded(stdout), self._bounded(stderr), digest, "process_completed")


class LocalHTTPCodingBackend:
    """Call an explicitly configured local HTTP inference endpoint.

    The endpoint is never discovered implicitly. The request uses the NOESIS
    chat contract (`message`, `preset`, `max_tokens`, `temperature`) and the
    response must contain a textual field; malformed or oversized responses
    fail closed. An optional bearer token is supplied only by the caller.
    """

    def __init__(
        self,
        endpoint: str,
        prompt: str,
        *,
        preset: str = "code",
        timeout_seconds: float = 900.0,
        output_limit: int = 200000,
        max_tokens: int = 768,
        temperature: float = 0.2,
        bearer_token: Optional[str] = None,
    ) -> None:
        if not isinstance(endpoint, str) or not endpoint.startswith(("http://", "https://")):
            raise CodingBackendError("explicit_http_endpoint_required")
        if not prompt:
            raise CodingBackendError("prompt_required")
        if not preset or timeout_seconds <= 0 or output_limit <= 0 or max_tokens <= 0:
            raise CodingBackendError("positive_limits_required")
        if temperature < 0:
            raise CodingBackendError("temperature_must_be_nonnegative")
        self.endpoint = endpoint
        self.prompt = prompt
        self.preset = preset
        self.timeout_seconds = float(timeout_seconds)
        self.output_limit = int(output_limit)
        self.max_tokens = int(max_tokens)
        self.temperature = float(temperature)
        self.bearer_token = bearer_token

    @property
    def request_digest(self) -> str:
        material = json.dumps({"endpoint": self.endpoint, "preset": self.preset, "prompt": self.prompt, "max_tokens": self.max_tokens, "temperature": self.temperature}, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def _bounded_text(self, value: str) -> str:
        if len(value) > self.output_limit:
            raise CodingBackendError("response_output_limit_exceeded")
        return value

    def _extract_text(self, value: Any) -> Optional[str]:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for key in ("response", "reply", "answer", "text", "content"):
                candidate = value.get(key)
                if isinstance(candidate, str):
                    return candidate
            message = value.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
        return None

    def run(self) -> BackendResult:
        payload = json.dumps({
            "message": self.prompt,
            "preset": self.preset,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }, separators=(",", ":")).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = "Bearer " + self.bearer_token
        request = Request(self.endpoint, data=payload, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read(self.output_limit + 1)
                if len(raw) > self.output_limit:
                    return BackendResult("failed", response.status, "", "", self.request_digest, "response_output_limit_exceeded")
                parsed = json.loads(raw.decode("utf-8"))
                text = self._extract_text(parsed)
                if text is None:
                    return BackendResult("failed", response.status, "", "", self.request_digest, "response_text_missing")
                return BackendResult("passed", response.status, self._bounded_text(text), "", self.request_digest, "http_completed")
        except HTTPError as exc:
            detail = exc.read(self.output_limit).decode("utf-8", errors="replace")
            return BackendResult("failed", exc.code, "", detail, self.request_digest, "http_error")
        except (TimeoutError, URLError, OSError) as exc:
            return BackendResult("timeout", None, "", "", self.request_digest, type(exc).__name__)
        except (UnicodeError, json.JSONDecodeError, CodingBackendError) as exc:
            return BackendResult("failed", None, "", "", self.request_digest, type(exc).__name__)


__all__ = ["BackendResult", "BoundedCodingBackend", "CodingBackendError", "LocalHTTPCodingBackend"]
