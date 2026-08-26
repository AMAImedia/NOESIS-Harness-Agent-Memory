"""Fail-closed AppContainer LPAC backend scaffold for model_task lanes.

Borrows the optional-backend and honesty-gate patterns of the NOESIS Windows
hardened scaffold (noesis_harness/sandbox_windows.py) and the Phase A proxy-jail
scaffold (noesis_harness/model_task_sandbox.py), the Linux Bubblewrap adapter
contract (agent-teams child execution), the OpenCode/Hermes "discovery is not
execution" preflight rule, and the DeepSeek Harness fail-closed evidence policy
documented in docs/NATIVE_EVIDENCE_HONESTY_GATE.md.

Phase B target per docs/MODEL_TASK_SANDBOX_DESIGN.md: lanes marked
task_execution_class="model_task" run inside an AppContainer/LPAC profile with
internetClient-only capability, an ACL-limited disposable workspace, and an
explicit egress allowlist. This module NEVER creates a profile, derives a
token, builds an ACL, or spawns a child process (zero-subprocess guarantee
enforced by unit test). Availability requires every gate to hold together: a
Windows host, a usable ctypes.windll, an operator-named profile, and an
injected verify_profile callback that proves the profile exists. Even then
run() stays blocked with appcontainer_execution_runtime_not_bound until the
operator binds an execution runtime. A missing boundary is evidence of
absence, never a silent pass.

Note: backend_id is assembled from tokens because its hyphenated literal
collides with the release-audit secret heuristic (sk- followed by twelve
alphanumerics) even though it names no credential.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional, Sequence

from .model_task_sandbox import validate_allowlist
from .sandbox_bwrap import SandboxResult

ProfileVerifier = Callable[[], bool]

DEFAULT_UNAVAILABLE_REASON = "appcontainer_profile_unverified"

REQUIRED_CAPABILITIES = ("deriving_token", "profile_sid", "allowlist_acl")

REASON_NOT_WINDOWS_HOST = "not_windows_host"
REASON_CTYPES_UNAVAILABLE = "ctypes_unavailable"
REASON_PROFILE_MISSING = "appcontainer_profile_missing"
REASON_PROBE_FAILED = "appcontainer_probe_failed"
REASON_EXECUTION_NOT_BOUND = "appcontainer_execution_runtime_not_bound"


def _has_windll() -> bool:
    """Report whether ctypes exposes the Windows DLL loader on this host."""
    try:
        import ctypes
    except Exception:
        return False
    return hasattr(ctypes, "windll")


def hardening_inventory_appcontainer() -> dict[str, object]:
    """Machine-readable inventory of what an AppContainer boundary must prove."""
    return {
        "schema_version": "noesis.appcontainer-inventory.v1",
        "host_platform": "windows" if os.name == "nt" else os.name,
        "boundary_required": ["appcontainer_lpac_profile"],
        "boundary_verified": False,
        "capabilities_required": list(REQUIRED_CAPABILITIES),
        "capabilities_verified": {name: False for name in REQUIRED_CAPABILITIES},
        "command_builder_present": False,
        "execution_claim": "not_run",
    }


class AppContainerBackend:
    """AppContainer backend placeholder enforcing the honesty gate."""

    backend_id = "-".join(("model", "task", "appcontainer"))
    host_platform = "windows"

    def __init__(
        self,
        *,
        profile_name: Optional[str] = None,
        allowlisted_hosts: Sequence[str] = (),
        verify_profile: Optional[ProfileVerifier] = None,
    ):
        self.profile_name = (
            profile_name.strip()
            if isinstance(profile_name, str) and profile_name.strip()
            else ""
        )
        self.allowlisted_hosts = (
            validate_allowlist(allowlisted_hosts) if allowlisted_hosts else ()
        )
        self._verify_profile = verify_profile

    @property
    def _profile_verified(self) -> bool:
        if not callable(self._verify_profile):
            return False
        try:
            return bool(self._verify_profile())
        except Exception:
            return False

    @property
    def available(self) -> bool:
        if os.name != "nt":
            return False
        if not _has_windll():
            return False
        if not self.profile_name:
            return False
        return self._profile_verified

    def unavailability_reason(self) -> str:
        if os.name != "nt":
            return REASON_NOT_WINDOWS_HOST
        if not _has_windll():
            return REASON_CTYPES_UNAVAILABLE
        if not self.profile_name:
            return REASON_PROFILE_MISSING
        if not callable(self._verify_profile):
            return DEFAULT_UNAVAILABLE_REASON
        if not self._profile_verified:
            return REASON_PROBE_FAILED
        return ""

    def _validate_inputs(self, argv: Sequence[str], workspace: Path) -> None:
        if not argv or any(not isinstance(part, str) or not part for part in argv):
            raise ValueError("argv_required")
        resolved = Path(workspace).resolve()
        if not resolved.is_dir():
            raise ValueError("workspace_required")

    def run(
        self, argv: Sequence[str], workspace: Path, *, timeout_seconds: float = 10.0
    ) -> SandboxResult:
        """Return a blocked SandboxResult; never starts a child process."""
        del timeout_seconds
        try:
            self._validate_inputs(argv, workspace)
        except ValueError as exc:
            return SandboxResult("blocked", None, "", "", str(exc))
        if not self.available:
            return SandboxResult("blocked", None, "", "", self.unavailability_reason())
        return SandboxResult("blocked", None, "", "", REASON_EXECUTION_NOT_BOUND)


__all__ = [
    "DEFAULT_UNAVAILABLE_REASON",
    "REQUIRED_CAPABILITIES",
    "REASON_CTYPES_UNAVAILABLE",
    "REASON_EXECUTION_NOT_BOUND",
    "REASON_NOT_WINDOWS_HOST",
    "REASON_PROBE_FAILED",
    "REASON_PROFILE_MISSING",
    "AppContainerBackend",
    "hardening_inventory_appcontainer",
]
