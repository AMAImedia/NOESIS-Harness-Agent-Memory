"""Bounded child-process execution boundary for approved tools and skills.

This is a process boundary, not a claim of a hardened OS sandbox. Network
isolation is fail-closed unless a separately verified sandbox adapter is used.
The parent never evaluates child/model output.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

from .gatekeeper import Gatekeeper
from .security import safe_path
from .sandbox_backend import SandboxBackend

MAX_OUTPUT_BYTES = 256 * 1024
MAX_ARG_COUNT = 64
_CREDENTIAL_OUTPUT_PATTERNS = (
    re.compile(r"(?i)\b(?:api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\b(?:hf|sk|ghp|github_pat)_[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]{12,}"),
)


class ChildExecutionError(ValueError):
    """Raised for invalid execution requests."""


@dataclass(frozen=True)
class ExecutionRequest:
    request_id: str
    argv: tuple[str, ...]
    workspace: str
    allowed_executables: tuple[str, ...]
    environment: Mapping[str, str] = field(default_factory=dict)
    timeout_seconds: float = 10.0
    output_limit: int = MAX_OUTPUT_BYTES
    network: bool = False
    skill_id: Optional[str] = None


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    request_id: str
    returncode: Optional[int]
    stdout: str
    stderr: str
    duration_ms: float
    reason: str
    sandboxed: bool = False


class ChildExecutionRuntime:
    """Run only explicitly approved, bounded, shell-free child processes."""

    def __init__(self, gatekeeper: Gatekeeper, *, environment_allowlist: Sequence[str] = (), sandbox_backend: SandboxBackend | None = None):
        self.gatekeeper = gatekeeper
        self.environment_allowlist = frozenset(str(key) for key in environment_allowlist)
        self.sandbox_backend = sandbox_backend

    @staticmethod
    def _basename(executable: str) -> str:
        return Path(executable).name.lower()

    def _validate(self, request: ExecutionRequest) -> Path:
        if not request.request_id or not request.argv or len(request.argv) > MAX_ARG_COUNT:
            raise ChildExecutionError("invalid_request_or_argv")
        if any(not isinstance(item, str) or not item for item in request.argv):
            raise ChildExecutionError("argv_items_must_be_nonempty_strings")
        if request.timeout_seconds <= 0 or request.timeout_seconds > 300:
            raise ChildExecutionError("timeout_out_of_bounds")
        if request.output_limit <= 0 or request.output_limit > MAX_OUTPUT_BYTES:
            raise ChildExecutionError("output_limit_out_of_bounds")
        if request.network:
            raise ChildExecutionError("network_isolation_unavailable_fail_closed")
        executable = self._basename(request.argv[0])
        allowed = {self._basename(item) for item in request.allowed_executables}
        if executable not in allowed:
            raise ChildExecutionError("executable_not_allowlisted")
        if any(item in {"-c", "--eval", "--execute", "-e"} for item in request.argv[1:]):
            raise ChildExecutionError("inline_code_execution_forbidden")
        workspace = Path(request.workspace).expanduser().resolve()
        if not workspace.is_dir():
            raise ChildExecutionError("workspace_missing")
        for key in request.environment:
            if key not in self.environment_allowlist:
                raise ChildExecutionError("environment_key_not_allowlisted:%s" % key)
        # If the command references a path argument, it must remain inside the workspace.
        for item in request.argv[1:]:
            if item.endswith((".py", ".pyz", ".sh", ".cmd", ".ps1")):
                raw_candidate = workspace / item
                if raw_candidate.is_symlink():
                    raise ChildExecutionError("entrypoint_missing_or_symlink")
                try:
                    candidate = safe_path(str(workspace), item)
                except PermissionError as exc:
                    raise ChildExecutionError("entrypoint_outside_workspace") from exc
                if candidate.is_symlink() or not candidate.is_file():
                    raise ChildExecutionError("entrypoint_missing_or_symlink")
        return workspace

    @staticmethod
    def _decode_bounded(data: bytes, limit: int) -> str:
        truncated = data[:limit]
        return truncated.decode("utf-8", "replace")

    @staticmethod
    def _redact_credential_like(text: str) -> tuple[str, bool]:
        found = False
        for pattern in _CREDENTIAL_OUTPUT_PATTERNS:
            text, count = pattern.subn("[REDACTED_CREDENTIAL]", text)
            found = found or bool(count)
        return text, found

    def run(self, request: ExecutionRequest) -> ExecutionResult:
        decision = self.gatekeeper.get(request.request_id)
        if not decision or decision.get("status") != "committed":
            return ExecutionResult("denied", request.request_id, None, "", "", 0.0, "gatekeeper_commit_required")
        try:
            workspace = self._validate(request)
        except ChildExecutionError as exc:
            return ExecutionResult("denied", request.request_id, None, "", "", 0.0, str(exc))
        if self.sandbox_backend is not None:
            if not self.sandbox_backend.available:
                return ExecutionResult("denied", request.request_id, None, "", "", 0.0, "sandbox_backend_unavailable")
            if request.environment:
                return ExecutionResult("denied", request.request_id, None, "", "", 0.0, "sandbox_backend_environment_unsupported")
            started = time.perf_counter()
            try:
                sandbox_result = self.sandbox_backend.run(request.argv, workspace, timeout_seconds=request.timeout_seconds)
            except Exception as exc:
                return ExecutionResult("failed", request.request_id, None, "", "", (time.perf_counter() - started) * 1000.0, "sandbox_launch_failed:%s" % type(exc).__name__, True)
            stdout_text, stdout_secret = self._redact_credential_like(sandbox_result.stdout)
            stderr_text, stderr_secret = self._redact_credential_like(sandbox_result.stderr)
            if stdout_secret or stderr_secret:
                return ExecutionResult("failed", request.request_id, sandbox_result.returncode, stdout_text, stderr_text, (time.perf_counter() - started) * 1000.0, "credential_like_output_blocked", True)
            if len(sandbox_result.stdout.encode("utf-8")) > request.output_limit or len(sandbox_result.stderr.encode("utf-8")) > request.output_limit:
                return ExecutionResult("failed", request.request_id, sandbox_result.returncode, stdout_text, stderr_text, (time.perf_counter() - started) * 1000.0, "output_budget_exceeded", True)
            status = "completed" if sandbox_result.status == "passed" else "timeout" if sandbox_result.status == "timed_out" else "failed"
            return ExecutionResult(status, request.request_id, sandbox_result.returncode, stdout_text, stderr_text, (time.perf_counter() - started) * 1000.0, sandbox_result.reason or "sandbox_%s" % status, True)
        environment = {key: os.environ[key] for key in self.environment_allowlist if key in os.environ}
        environment.update({key: str(value) for key, value in request.environment.items()})
        started = time.perf_counter()
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        kwargs = {"start_new_session": os.name != "nt", "creationflags": creationflags}
        try:
            process = subprocess.Popen(
                list(request.argv), cwd=str(workspace), env=environment,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                shell=False, close_fds=(os.name != "nt"), **kwargs,
            )
            try:
                stdout, stderr = process.communicate(timeout=request.timeout_seconds)
            except subprocess.TimeoutExpired:
                if os.name != "nt":
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except OSError:
                        process.terminate()
                else:
                    process.terminate()
                stdout, stderr = process.communicate(timeout=2.0)
                return ExecutionResult("timeout", request.request_id, process.returncode, self._decode_bounded(stdout, request.output_limit), self._decode_bounded(stderr, request.output_limit), (time.perf_counter() - started) * 1000.0, "timeout_budget_exceeded")
        except (OSError, subprocess.SubprocessError) as exc:
            return ExecutionResult("failed", request.request_id, None, "", "", (time.perf_counter() - started) * 1000.0, "launch_failed:%s" % type(exc).__name__)
        stdout_text = self._decode_bounded(stdout, request.output_limit)
        stderr_text = self._decode_bounded(stderr, request.output_limit)
        stdout_text, stdout_secret = self._redact_credential_like(stdout_text)
        stderr_text, stderr_secret = self._redact_credential_like(stderr_text)
        if stdout_secret or stderr_secret:
            return ExecutionResult("failed", request.request_id, process.returncode, stdout_text, stderr_text, (time.perf_counter() - started) * 1000.0, "credential_like_output_blocked")
        if len(stdout) > request.output_limit or len(stderr) > request.output_limit:
            return ExecutionResult("failed", request.request_id, process.returncode, stdout_text, stderr_text, (time.perf_counter() - started) * 1000.0, "output_budget_exceeded")
        status = "completed" if process.returncode == 0 else "failed"
        return ExecutionResult(status, request.request_id, process.returncode, stdout_text, stderr_text, (time.perf_counter() - started) * 1000.0, "exit_%s" % process.returncode)


__all__ = ["MAX_OUTPUT_BYTES", "ExecutionRequest", "ExecutionResult", "ChildExecutionError", "ChildExecutionRuntime"]
