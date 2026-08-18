"""macOS sandbox-exec backend adapter.

The backend is intentionally unavailable off macOS. It does not claim native
verification on Linux and keeps the profile explicit for operator review.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .sandbox_bwrap import SandboxResult, SandboxUnavailable
from .process_control import terminate_process_tree


class MacOSSandboxBackend:
    backend_id = "macos-sandbox-exec"
    host_platform = "macos"

    def __init__(self, *, executable: str = "sandbox-exec", max_output_bytes: int = 64 * 1024):
        self.executable = shutil.which(executable)
        self.max_output_bytes = max_output_bytes

    @property
    def available(self) -> bool:
        return self.executable is not None and os.name == "posix" and os.uname().sysname == "Darwin"

    @staticmethod
    def profile(workspace: Path) -> str:
        path = json.dumps(str(workspace.resolve()))
        return " ".join((
            "(version 1)",
            "(deny default)",
            "(allow process-exec)",
            "(allow process-fork)",
            "(allow file-read* (subpath \"/usr\"))",
            "(allow file-read* (subpath \"/System\"))",
            "(allow file-read* (subpath \"/private\"))",
            "(allow file-read* (subpath " + path + "))",
            "(allow file-write* (subpath " + path + "))",
            "(deny network*)",
        ))

    def command(self, argv: Sequence[str], workspace: Path) -> list[str]:
        if not self.available:
            raise SandboxUnavailable("macos_sandbox_unavailable")
        if not argv or any(not isinstance(part, str) or not part for part in argv):
            raise ValueError("argv_required")
        workspace = workspace.resolve()
        if not workspace.is_dir():
            raise ValueError("workspace_required")
        return [self.executable, "-p", self.profile(workspace), "--", *argv]

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


__all__ = ["MacOSSandboxBackend"]
