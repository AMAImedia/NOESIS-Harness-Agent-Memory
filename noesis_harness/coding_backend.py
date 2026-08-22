"""Bounded coding-backend process adapter.

Patterns adapted from NOESIS Gatekeeper/ChildExecutionRuntime, Hermes bounded
turns, agent-teams isolation, and process-group cancellation guidance. The
adapter is stdlib-only and never chooses a model or executes an unconfigured
command; callers must provide an explicit argv, contained worktree, timeout,
and output budget.
"""
from __future__ import annotations

import hashlib
import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple


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


__all__ = ["BackendResult", "BoundedCodingBackend", "CodingBackendError"]
