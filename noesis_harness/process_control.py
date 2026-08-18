"""Bounded process-tree termination helpers for child execution backends."""
from __future__ import annotations

import os
import signal
import subprocess
import time
from typing import Any


def terminate_process_tree(process: Any, *, grace_seconds: float = 0.25) -> str:
    """Terminate a process group/job without shell execution; return mechanism."""
    if process.poll() is not None:
        return "already_exited"
    if os.name != "nt":
        try:
            os.killpg(process.pid, signal.SIGTERM)
            mechanism = "posix_process_group_sigterm"
        except OSError:
            process.terminate()
            mechanism = "process_terminate_fallback"
        deadline = time.monotonic() + grace_seconds
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
                mechanism = "posix_process_group_sigkill"
            except OSError:
                process.kill()
                mechanism = "process_kill_fallback"
        return mechanism
    process.terminate()
    deadline = time.monotonic() + grace_seconds
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    if process.poll() is None:
        try:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            mechanism = "windows_taskkill_tree"
        except OSError:
            process.kill()
            mechanism = "windows_process_kill_fallback"
    else:
        mechanism = "windows_process_terminate"
    return mechanism


__all__ = ["terminate_process_tree"]
