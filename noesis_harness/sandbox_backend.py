"""Common contracts for optional OS sandbox backends.

Backends are selected explicitly. Availability and host evidence are reported
rather than silently emulated on a different operating system.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence


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


__all__ = ["BackendConformanceResult", "SandboxBackend", "inspect_backend"]
