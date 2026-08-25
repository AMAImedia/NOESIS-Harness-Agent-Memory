"""Fail-closed proxy-jail backend scaffold for model_task lanes.

Borrows the optional-backend and honesty-gate patterns of the NOESIS Windows
hardened scaffold (noesis_harness/sandbox_windows.py), the Linux Bubblewrap
adapter contract (agent-teams child execution), the OpenCode/Hermes "discovery
is not execution" preflight rule, and the DeepSeek Harness fail-closed evidence
policy documented in docs/NATIVE_EVIDENCE_HONESTY_GATE.md.

Purpose: lanes marked task_execution_class="model_task" must reach an
explicitly allowlisted set of model-api hosts while every other destination
stays denied. Phase A enforcement is a loopback allowlist proxy advertised via
the standard HTTP(S)_PROXY environment variables. That is an advisory
boundary, not a kernel one: a child that ignores the proxy environment escapes
it. The module therefore reports available=False until an operator-supplied
verify_proxy_boundary callback proves the boundary, and it NEVER spawns a
child process itself (zero-subprocess guarantee enforced by unit test). A
missing or unverified boundary is evidence of absence, never a silent pass.

Design rationale and phased plan: docs/MODEL_TASK_SANDBOX_DESIGN.md.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional, Sequence

from .sandbox_bwrap import SandboxResult, SandboxUnavailable

BoundaryVerifier = Callable[[], bool]

DEFAULT_UNAVAILABLE_REASON = "model_task_proxy_boundary_unverified"
PROXY_HOST = "127.0.0.1"
PLACEHOLDER_PROXY_PORT = 0
LOOPBACK_NO_PROXY_ENTRIES = ("localhost", "127.0.0.1", "::1")

_HOST_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$"
)


def validate_allowlist(allowlisted_hosts: Optional[Sequence[object]]) -> tuple[str, ...]:
    """Normalize and validate the egress allowlist; fails closed on any doubt."""
    if not allowlisted_hosts:
        raise ValueError("allowlisted_hosts_required")
    if isinstance(allowlisted_hosts, str):
        raise ValueError("allowlisted_hosts_sequence_required")
    normalized: list[str] = []
    for host in allowlisted_hosts:
        if not isinstance(host, str):
            raise ValueError("invalid_allowlisted_host:%r" % (host,))
        candidate = host.strip().casefold()
        if not candidate or len(candidate) > 253 or not _HOST_RE.match(candidate):
            raise ValueError("invalid_allowlisted_host:%s" % candidate)
        if candidate not in normalized:
            normalized.append(candidate)
    return tuple(normalized)


def proxy_env_for(
    allowlisted_hosts: Sequence[str], *, port: int = PLACEHOLDER_PROXY_PORT
) -> dict[str, str]:
    """Build the deterministic proxy-jail environment for a lane.

    Returns upper- and lower-case HTTP(S)_PROXY entries pointing at the
    loopback proxy endpoint and NO_PROXY entries that exempt loopback targets
    only. The allowlisted model-api hosts deliberately stay OUT of NO_PROXY:
    their traffic is the traffic being jailed. Port 0 is the documented
    placeholder for the operator-chosen listener port.
    """
    validated_port = int(port)
    if not 0 <= validated_port <= 65535:
        raise ValueError("invalid_proxy_port:%d" % validated_port)
    validate_allowlist(allowlisted_hosts)
    endpoint = "http://%s:%d" % (PROXY_HOST, validated_port)
    no_proxy = ",".join(LOOPBACK_NO_PROXY_ENTRIES)
    return {
        "HTTP_PROXY": endpoint,
        "HTTPS_PROXY": endpoint,
        "http_proxy": endpoint,
        "https_proxy": endpoint,
        "NO_PROXY": no_proxy,
        "no_proxy": no_proxy,
    }


def network_inventory() -> dict[str, object]:
    """Machine-readable inventory of what a model_task boundary must prove."""
    return {
        "schema_version": "noesis.model-task-sandbox-inventory.v1",
        "host_platform": "any",
        "boundary_required": ["loopback_allowlist_proxy_egress_jail"],
        "boundary_verified": False,
        "enforcement_strength": "advisory",
        "proxy_endpoint": "http://%s:%d" % (PROXY_HOST, PLACEHOLDER_PROXY_PORT),
        "execution_claim": "not_run",
    }


class ModelTaskSandboxBackend:
    """Proxy-jail backend placeholder enforcing the honesty gate."""

    backend_id = "model-task-proxy"
    host_platform = "any"

    def __init__(
        self,
        *,
        allowlisted_hosts: Sequence[str],
        verify_proxy_boundary: Optional[BoundaryVerifier] = None,
    ):
        self.allowlisted_hosts = validate_allowlist(allowlisted_hosts)
        self._verify_proxy_boundary = verify_proxy_boundary

    @property
    def _boundary_verified(self) -> bool:
        if not callable(self._verify_proxy_boundary):
            return False
        try:
            return bool(self._verify_proxy_boundary())
        except Exception:
            return False

    @property
    def available(self) -> bool:
        return self._boundary_verified

    def unavailability_reason(self) -> str:
        if not callable(self._verify_proxy_boundary):
            return DEFAULT_UNAVAILABLE_REASON
        if not self._boundary_verified:
            return "model_task_proxy_boundary_check_failed"
        return ""

    def egress_policy(self) -> dict[str, object]:
        """Declare the lane egress policy, including its advisory limits."""
        return {
            "schema_version": "noesis.model-task-egress-policy.v1",
            "backend_id": self.backend_id,
            "default": "deny",
            "allowed_hosts": list(self.allowlisted_hosts),
            "enforcement": "environment-proxy",
            "enforcement_strength": "advisory",
            "known_escape": "children_ignoring_proxy_env_are_not_contained",
            "execution_claim": "not_run",
        }

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
        return SandboxResult("blocked", None, "", "", "model_task_execution_runtime_not_bound")


__all__ = [
    "DEFAULT_UNAVAILABLE_REASON",
    "LOOPBACK_NO_PROXY_ENTRIES",
    "PLACEHOLDER_PROXY_PORT",
    "PROXY_HOST",
    "ModelTaskSandboxBackend",
    "network_inventory",
    "proxy_env_for",
    "validate_allowlist",
]
