"""Fail-closed Windows hardened execution backend scaffold.

Borrows the optional-backend and honesty-gate patterns of the NOESIS Linux
Bubblewrap adapter (agent-teams child execution), the OpenCode/Hermes
"discovery is not execution" preflight rule, and the DeepSeek Harness
fail-closed evidence policy documented in docs/NATIVE_EVIDENCE_HONESTY_GATE.md.

The backend NEVER spawns a child process in this module: until a verified
OS hardening boundary (AppContainer or restricted token) and an explicit
command builder are supplied by the operator, every entry point reports
unavailable/not_run/blocked. A missing boundary is evidence of absence,
never a silent pass.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional, Sequence

from .sandbox_bwrap import SandboxResult, SandboxUnavailable

BoundaryVerifier = Callable[[], bool]
CommandBuilder = Callable[[Sequence[str], Path], list[str]]

DEFAULT_UNAVAILABLE_REASON = "windows_hardening_boundary_unverified"


def hardening_inventory() -> dict[str, object]:
    """Machine-readable inventory of what a Windows boundary must prove."""
    return {
        "schema_version": "noesis.windows-hardening-inventory.v1",
        "host_platform": "windows" if os.name == "nt" else os.name,
        "boundary_required": ["appcontainer_or_restricted_token"],
        "boundary_verified": False,
        "command_builder_present": False,
        "execution_claim": "not_run",
    }


class WindowsSandboxBackend:
    """Windows hardened backend placeholder enforcing the honesty gate."""

    backend_id = "windows-hardened"
    host_platform = "windows"

    def __init__(
        self,
        *,
        boundary_verifier: Optional[BoundaryVerifier] = None,
        command_builder: Optional[CommandBuilder] = None,
    ):
        self._boundary_verifier = boundary_verifier
        self._command_builder = command_builder

    @property
    def _boundary_verified(self) -> bool:
        if os.name != "nt":
            return False
        if not callable(self._boundary_verifier):
            return False
        try:
            return bool(self._boundary_verifier())
        except Exception:
            return False

    @property
    def available(self) -> bool:
        return self._boundary_verified and callable(self._command_builder)

    def unavailability_reason(self) -> str:
        if os.name != "nt":
            return "not_windows_host"
        if not callable(self._boundary_verifier):
            return DEFAULT_UNAVAILABLE_REASON
        if not self._boundary_verified:
            return "windows_hardening_boundary_check_failed"
        if not callable(self._command_builder):
            return "windows_command_builder_missing"
        return ""

    def command(self, argv: Sequence[str], workspace: Path) -> list[str]:
        if not argv or any(not isinstance(part, str) or not part for part in argv):
            raise ValueError("argv_required")
        workspace = workspace.resolve()
        if not workspace.is_dir():
            raise ValueError("workspace_required")
        if not self.available:
            raise SandboxUnavailable(self.unavailability_reason())
        built = self._command_builder(argv, workspace)
        if not isinstance(built, list) or not all(isinstance(part, str) and part for part in built):
            raise SandboxUnavailable("windows_command_builder_invalid")
        if "--" not in built:
            raise SandboxUnavailable("windows_command_builder_separator_missing")
        return built

    def run(self, argv: Sequence[str], workspace: Path, *, timeout_seconds: float = 10.0) -> SandboxResult:
        del timeout_seconds
        if not self.available:
            return SandboxResult("blocked", None, "", "", self.unavailability_reason())
        try:
            command = self.command(argv, workspace)
        except (ValueError, SandboxUnavailable) as exc:
            return SandboxResult("blocked", None, "", "", str(exc))
        return SandboxResult("blocked", None, "", "", "windows_execution_runtime_not_bound:" + "\0".join(command[:1]))


__all__ = ["DEFAULT_UNAVAILABLE_REASON", "WindowsSandboxBackend", "hardening_inventory"]
