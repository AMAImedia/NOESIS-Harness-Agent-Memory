"""Bubblewrap hardened backend adapter.

This backend is Linux-only and optional. It is not silently substituted on
Windows/macOS. Every invocation is explicit argv, with a writable workspace
and read-only system mounts; network namespace is unshared by default.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .process_control import terminate_process_tree


class SandboxUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class SandboxResult:
    status: str
    returncode: int | None
    stdout: str
    stderr: str
    reason: str = ""


class BubblewrapBackend:
    backend_id = "linux-bubblewrap"
    host_platform = "linux"

    def __init__(self, *, executable: str = "bwrap", max_output_bytes: int = 64 * 1024):
        self.executable = shutil.which(executable)
        self.max_output_bytes = max_output_bytes

    @property
    def available(self) -> bool:
        return self.executable is not None and os.name == "posix"

    def command(self, argv: Sequence[str], workspace: Path) -> list[str]:
        if not self.available:
            raise SandboxUnavailable("bubblewrap_unavailable")
        if not argv or any(not isinstance(part, str) or not part for part in argv):
            raise ValueError("argv_required")
        workspace = workspace.resolve()
        if not workspace.is_dir():
            raise ValueError("workspace_required")
        return [
            self.executable,
            "--die-with-parent",
            "--new-session",
            "--unshare-all",
            "--unshare-net",
            "--clearenv",
            "--ro-bind", "/usr", "/usr",
            "--ro-bind", "/bin", "/bin",
            "--ro-bind", "/lib", "/lib",
            "--ro-bind", "/lib64", "/lib64",
            "--ro-bind", "/etc", "/etc",
            "--proc", "/proc",
            "--dev", "/dev",
            "--tmpfs", "/tmp",
            "--bind", str(workspace), "/workspace",
            "--chdir", "/workspace",
            "--setenv", "HOME", "/workspace/home",
            "--setenv", "PATH", "/usr/bin:/bin",
            "--",
            *argv,
        ]

    def run(self, argv: Sequence[str], workspace: Path, *, timeout_seconds: float = 10.0) -> SandboxResult:
        command = self.command(argv, workspace)
        proc = subprocess.Popen(command, cwd=str(workspace), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            stdout, stderr = proc.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            mechanism = terminate_process_tree(proc)
            stdout, stderr = proc.communicate(timeout=2.0)
            return SandboxResult("timed_out", proc.returncode, stdout[: self.max_output_bytes], stderr[: self.max_output_bytes], "timeout:%s" % mechanism)
        stdout = stdout[: self.max_output_bytes]
        stderr = stderr[: self.max_output_bytes]
        status = "passed" if proc.returncode == 0 else "failed"
        reason = "" if proc.returncode == 0 else "child_nonzero"
        return SandboxResult(status, proc.returncode, stdout, stderr, reason)


__all__ = ["BubblewrapBackend", "SandboxResult", "SandboxUnavailable"]
