"""Common contracts for optional OS sandbox backends.

Backends are selected explicitly. Availability and host evidence are reported
rather than silently emulated on a different operating system.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class BackendConformanceResult:
    backend_id: str
    host_platform: str
    available: bool
    checks: tuple[tuple[str, str], ...]
    reason: str = ""

    @property
    def passed(self) -> bool:
        return self.available and all(status == "passed" for _, status in self.checks)

    def as_dict(self) -> dict[str, object]:
        return {
            "backend_id": self.backend_id,
            "host_platform": self.host_platform,
            "available": self.available,
            "checks": [{"name": name, "status": status} for name, status in self.checks],
            "reason": self.reason,
            "status": "passed" if self.passed else "not_run" if not self.available else "failed",
        }


class SandboxBackend(Protocol):
    backend_id: str
    host_platform: str
    available: bool

    def command(self, argv: Sequence[str], workspace: Path) -> list[str]: ...


def run_conformance(backend: SandboxBackend, *, workspace: Path) -> BackendConformanceResult:
    """Run a bounded write/exit probe after command-level inspection.

    The runner never substitutes an unavailable backend. It records `not_run`
    for unavailable hosts and only adds execution checks when the selected
    backend explicitly exposes a `run` method.
    """
    inspected = inspect_backend(backend, workspace=workspace)
    if not inspected.available:
        return inspected
    runner = getattr(backend, "run", None)
    if not callable(runner):
        return BackendConformanceResult(backend.backend_id, backend.host_platform, True, inspected.checks + (("execution_runner", "failed"),), "backend_run_method_required")
    marker = workspace / ".noesis-conformance-marker"
    code = "from pathlib import Path; Path('.noesis-conformance-marker').write_text('conformance', encoding='utf-8'); print('conformance')"
    try:
        result: Any = runner(("/usr/bin/python3", "-c", code), workspace, timeout_seconds=5.0)
        checks = list(inspected.checks)
        checks.append(("execution_runner", "passed" if result.status == "passed" else "failed"))
        checks.append(("workspace_write", "passed" if marker.is_file() and marker.read_text(encoding="utf-8") == "conformance" else "failed"))
        checks.append(("process_exit", "passed" if result.returncode == 0 else "failed"))
        reason = "" if all(status == "passed" for _, status in checks) else (result.reason or "conformance_probe_failed")
        return BackendConformanceResult(backend.backend_id, backend.host_platform, True, tuple(checks), reason)
    except Exception as exc:
        return BackendConformanceResult(backend.backend_id, backend.host_platform, True, inspected.checks + (("execution_runner", "failed"),), "conformance_probe_error:%s" % type(exc).__name__)
    finally:
        try:
            marker.unlink()
        except FileNotFoundError:
            pass


def inspect_backend(backend: SandboxBackend, *, probe_argv: Sequence[str] = ("/usr/bin/printf", "conformance"), workspace: Path) -> BackendConformanceResult:
    """Validate command-level invariants without executing a child process."""
    if not backend.available:
        return BackendConformanceResult(backend.backend_id, backend.host_platform, False, (), "backend_unavailable_on_host")
    try:
        command = backend.command(probe_argv, workspace)
    except Exception as exc:
        return BackendConformanceResult(backend.backend_id, backend.host_platform, True, (("command_build", "failed"),), type(exc).__name__)
    rendered = "\0".join(command)
    checks = (
        ("argv_present", "passed" if rendered else "failed"),
        ("workspace_binding", "passed" if str(workspace.resolve()) in rendered or "/workspace" in rendered else "failed"),
        ("network_policy_declared", "passed" if any(marker in rendered for marker in ("unshare-net", "network", "network-outbound")) else "failed"),
        ("shell_not_selected", "passed" if "shell" not in command else "failed"),
    )
    return BackendConformanceResult(backend.backend_id, backend.host_platform, True, checks)


__all__ = ["BackendConformanceResult", "SandboxBackend", "inspect_backend", "run_conformance"]
