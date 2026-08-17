"""Cross-platform child-runtime supervision for the NOESIS control plane.

Patterns are borrowed from deepseek-harness process boundaries, Hermes local
runtime management, and the NOESIS deny-by-default control plane. The
supervisor launches only an owner-supplied argv sequence, never evaluates
model text, binds readiness checks to loopback, and keeps runtime logs.
"""

import json
import os
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence, Tuple

from .user_data import user_data_paths


@dataclass(frozen=True)
class RuntimeStatus:
    state: str
    host: str
    port: int
    pid: Optional[int]
    restart_count: int
    log_path: str
    reason: str


class ChildRuntimeSupervisor:
    """Own one local child process and expose deterministic lifecycle state."""

    def __init__(
        self,
        command_factory: Callable[[str, int], Sequence[str]],
        *,
        runtime_dir: Optional[str] = None,
        host: str = "127.0.0.1",
        readiness_path: str = "/health",
        startup_timeout: float = 5.0,
        readiness_interval: float = 0.05,
        max_restarts: int = 1,
        environment: Optional[Mapping[str, str]] = None,
    ):
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("child runtime must bind to loopback")
        if not readiness_path.startswith("/"):
            raise ValueError("readiness_path must start with /")
        if startup_timeout <= 0 or readiness_interval <= 0:
            raise ValueError("timeouts must be positive")
        if max_restarts < 0:
            raise ValueError("max_restarts must be non-negative")
        self.command_factory = command_factory
        self.runtime_dir = Path(runtime_dir).expanduser().resolve() if runtime_dir else user_data_paths(create=False).runtime
        self.host = host
        self.readiness_path = readiness_path
        self.startup_timeout = float(startup_timeout)
        self.readiness_interval = float(readiness_interval)
        self.max_restarts = int(max_restarts)
        self.environment = dict(environment or {})
        self._process = None
        self._log_handle = None
        self._port = 0
        self._restart_count = 0
        self._log_path = self.runtime_dir / "runtime.log"
        self._lock = threading.RLock()
        self._state = "stopped"
        self._reason = "not_started"

    @staticmethod
    def _free_loopback_port(host: str) -> int:
        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])

    def _status(self) -> RuntimeStatus:
        pid = self._process.pid if self._process is not None and self._process.poll() is None else None
        return RuntimeStatus(self._state, self.host, self._port, pid, self._restart_count, str(self._log_path), self._reason)

    @property
    def status(self) -> RuntimeStatus:
        with self._lock:
            return self._status()

    def _launch(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self._log_handle = open(self._log_path, "ab", buffering=0)
        command = tuple(str(item) for item in self.command_factory(self.host, self._port))
        if not command or any(not item for item in command):
            self._log_handle.close()
            self._log_handle = None
            raise ValueError("command_factory returned an empty command")
        env = os.environ.copy()
        env.update(self.environment)
        env["NOESIS_HOST"] = self.host
        env["NOESIS_PORT"] = str(self._port)
        self._process = subprocess.Popen(
            command,
            cwd=str(self.runtime_dir),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=self._log_handle,
            stderr=subprocess.STDOUT,
            close_fds=(os.name != "nt"),
        )

    def _ready(self) -> bool:
        url = "http://[%s]:%d%s" % (self.host, self._port, self.readiness_path) if ":" in self.host else "http://%s:%d%s" % (self.host, self._port, self.readiness_path)
        request = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=max(self.readiness_interval * 2.0, 0.2)) as response:
                if response.status != 200:
                    return False
                payload = json.loads(response.read().decode("utf-8"))
                return isinstance(payload, dict) and payload.get("status") in {"ready", "degraded"}
        except (OSError, urllib.error.URLError, ValueError, json.JSONDecodeError):
            return False

    def start(self) -> RuntimeStatus:
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return self._status()
            self._port = self._free_loopback_port(self.host)
            self._restart_count = 0
            self._state = "starting"
            self._reason = "launching"
            self._launch()
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            with self._lock:
                process = self._process
                if process is None or process.poll() is not None:
                    self._state = "crashed"
                    self._reason = "child_exited_before_ready"
                    self._close_log()
                    return self._status()
            if self._ready():
                with self._lock:
                    self._state = "ready"
                    self._reason = "readiness_verified"
                    return self._status()
            time.sleep(self.readiness_interval)
        with self._lock:
            self._state = "failed"
            self._reason = "readiness_timeout"
            self._terminate_locked()
            return self._status()

    def recover_if_crashed(self) -> RuntimeStatus:
        with self._lock:
            crashed = self._process is None or self._process.poll() is not None
            if not crashed or self._state == "stopped":
                return self._status()
            if self._restart_count >= self.max_restarts:
                self._state = "failed"
                self._reason = "restart_budget_exhausted"
                return self._status()
            self._close_log()
            self._restart_count += 1
            self._port = self._free_loopback_port(self.host)
            self._state = "starting"
            self._reason = "recovering_after_crash"
            self._launch()
        return self._wait_for_ready()

    def _wait_for_ready(self) -> RuntimeStatus:
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            with self._lock:
                if self._process is None or self._process.poll() is not None:
                    self._state = "crashed"
                    self._reason = "recovery_child_exited_before_ready"
                    self._close_log()
                    return self._status()
            if self._ready():
                with self._lock:
                    self._state = "ready"
                    self._reason = "recovery_readiness_verified"
                    return self._status()
            time.sleep(self.readiness_interval)
        with self._lock:
            self._state = "failed"
            self._reason = "recovery_readiness_timeout"
            self._terminate_locked()
            return self._status()

    def _close_log(self) -> None:
        if self._log_handle is not None:
            self._log_handle.close()
            self._log_handle = None

    def _terminate_locked(self) -> None:
        process = self._process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2.0)
        self._close_log()

    def stop(self) -> RuntimeStatus:
        with self._lock:
            self._terminate_locked()
            self._state = "stopped"
            self._reason = "clean_stop"
            return self._status()

    def __enter__(self) -> "ChildRuntimeSupervisor":
        self.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.stop()


__all__ = ["ChildRuntimeSupervisor", "RuntimeStatus"]
