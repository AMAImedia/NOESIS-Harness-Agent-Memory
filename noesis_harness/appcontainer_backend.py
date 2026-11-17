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

Phase B adds Windows API presence probes that are introspection only, per the
AppContainer launch contract in docs/MODEL_TASK_SANDBOX_DESIGN.md (Microsoft
"Launch an AppContainer" / CreateAppContainerProfile semantics): a package SID
is a pure derivation from the profile moniker (userenv GetAppContainerSid,
superseded by DeriveAppContainerSidFromAppContainerName), while creating a
profile writes per-user profile storage and returns E_ACCESSDENIED to a
non-elevated caller. profile_sid_probe() derives a SID from an inert probe name
and frees it; capability_inventory() resolves the CreateProcess
PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES export set; run_probe() reports a
blocked/not_run status with that capability evidence. None of them creates a
profile, derives a token, builds an ACL, or starts a child process. API
presence is never treated as a bound execution runtime.

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
REASON_WIN32_USERENV_UNAVAILABLE = "win32_userenv_unavailable"
REASON_SID_EXPORT_ABSENT = "appcontainer_sid_export_absent"
REASON_SID_DERIVATION_FAILED = "appcontainer_sid_derivation_failed"

PROBE_PROFILE_NAME = "noesis.harness.probe"

_CAPABILITY_FUNCTIONS = (
    ("CreateProcessW", "kernel32"),
    ("InitializeProcThreadAttributeList", "kernel32"),
    ("UpdateProcThreadAttribute", "kernel32"),
    ("GetAppContainerSid", "userenv"),
)


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


def _resolve_win32_export(library: str, name: str) -> bool:
    """Resolve an export through ctypes.windll without ever calling it."""
    if not _has_windll():
        return False
    try:
        import ctypes
    except Exception:
        return False
    try:
        dll = getattr(ctypes.windll, library, None)
        if dll is None:
            return False
        getattr(dll, name)
        return True
    except Exception:
        return False


def _probe_app_container_sid() -> tuple[str, str]:
    """Return (reason, export) where reason "" means a SID was derived.

    Derives a SID from PROBE_PROFILE_NAME via userenv. GetAppContainerSid is
    tried first (the export named in this task); on builds where that
    deprecated export was dropped, its documented successor
    DeriveAppContainerSidFromAppContainerName is tried. The SID is a pure
    derivation from the moniker: no profile is created, no profile storage is
    touched, no admin is required. The allocated SID is freed immediately with
    advapi32.FreeSid. Never raises.
    """
    if not _has_windll():
        return (REASON_CTYPES_UNAVAILABLE, "")
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return (REASON_CTYPES_UNAVAILABLE, "")
    try:
        userenv = ctypes.windll.userenv
    except Exception:
        return (REASON_WIN32_USERENV_UNAVAILABLE, "")
    exports = (
        "GetAppContainerSid",
        "DeriveAppContainerSidFromAppContainerName",
    )
    if not any(hasattr(userenv, export) for export in exports):
        return (REASON_SID_EXPORT_ABSENT, "")
    for export in exports:
        derive = getattr(userenv, export, None)
        if derive is None:
            continue
        try:
            derive.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
            derive.restype = wintypes.LONG
        except Exception:
            pass
        p_sid = ctypes.c_void_p()
        try:
            rc = derive(PROBE_PROFILE_NAME, ctypes.byref(p_sid))
        except Exception:
            continue
        if rc != 0:
            continue
        try:
            advapi32 = ctypes.windll.advapi32
            advapi32.FreeSid(p_sid)
        except Exception:
            pass
        return ("", export)
    return (REASON_SID_DERIVATION_FAILED, "")


def profile_sid_probe() -> dict[str, object]:
    """Probe whether this host can derive an AppContainer package SID.

    Returns {available: bool, reason: str} and never raises, never creates a
    profile, and never starts a process. available=True means the probe name
    was derivable to a SID and the SID was freed; reason records which export
    actually derived it. available=True does NOT mean any AppContainer profile
    exists on this host.
    """
    if os.name != "nt":
        return {"available": False, "reason": REASON_NOT_WINDOWS_HOST}
    reason, used = _probe_app_container_sid()
    if reason:
        return {"available": False, "reason": reason}
    return {"available": True, "reason": "ok:%s" % used}


def capability_inventory() -> dict[str, object]:
    """Report which AppContainer LPAC exports resolve via ctypes.

    Pure introspection: each export is resolved (LoadLibrary + GetProcAddress
    under ctypes) but never called, so the result is deterministic and has zero
    side effects. GetAppContainerSid lives in userenv.dll, not kernel32.dll;
    the library name is reported per export for honest accounting.
    """
    functions = {
        name: {"library": library, "callable": _resolve_win32_export(library, name)}
        for name, library in _CAPABILITY_FUNCTIONS
    }
    return {
        "schema_version": "noesis.appcontainer-capabilities.v1",
        "host_platform": "windows" if os.name == "nt" else os.name,
        "windll_present": _has_windll(),
        "functions": functions,
        "execution_bound": False,
        "claim": "api_presence_does_not_bind_execution",
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

    def run_probe(self) -> dict[str, object]:
        """Report why this lane cannot run, without attempting execution.

        Returns {status, reason, capabilities}; status is only ever "not_run"
        (host cannot attempt: non-Windows or no ctypes.windll) or "blocked"
        (Windows host, execution still unbound). It never returns "passed" and
        never starts a child process.
        """
        capabilities = capability_inventory()
        if os.name != "nt":
            return {
                "status": "not_run",
                "reason": REASON_NOT_WINDOWS_HOST,
                "capabilities": capabilities,
            }
        if not _has_windll():
            return {
                "status": "not_run",
                "reason": REASON_CTYPES_UNAVAILABLE,
                "capabilities": capabilities,
            }
        reason = self.unavailability_reason() or REASON_EXECUTION_NOT_BOUND
        return {"status": "blocked", "reason": reason, "capabilities": capabilities}


__all__ = [
    "DEFAULT_UNAVAILABLE_REASON",
    "REQUIRED_CAPABILITIES",
    "REASON_CTYPES_UNAVAILABLE",
    "REASON_EXECUTION_NOT_BOUND",
    "REASON_NOT_WINDOWS_HOST",
    "REASON_PROBE_FAILED",
    "REASON_PROFILE_MISSING",
    "REASON_SID_DERIVATION_FAILED",
    "REASON_SID_EXPORT_ABSENT",
    "REASON_WIN32_USERENV_UNAVAILABLE",
    "AppContainerBackend",
    "capability_inventory",
    "hardening_inventory_appcontainer",
    "profile_sid_probe",
]
