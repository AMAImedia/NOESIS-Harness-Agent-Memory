"""Version-pinned declarative Hermes gateway boundary for NOESIS.

Patterns are borrowed from Hermes bridge capability contracts, deepseek-harness
plugin boundaries, and NOESIS deny-by-default scopes. The adapter validates
metadata only; it never stores credentials, calls a gateway, or executes tool
or model output.
"""

from dataclasses import dataclass
from typing import Mapping, Optional, Tuple
from urllib.parse import urlparse

from .bridge_discovery import BridgeCandidate

HERMES_SUPPORTED_SCOPES = frozenset({"health.read", "models.read", "chat", "tools.invoke"})
HERMES_FORBIDDEN_SCOPE_PREFIXES = ("filesystem.", "shell.", "process.", "network.write")


class HermesGatewayError(ValueError):
    """Raised when a Hermes gateway declaration violates a security boundary."""


@dataclass(frozen=True)
class HermesGatewayConfig:
    gateway_id: str
    base_url: str
    pinned_version: str
    deployment: str = "local"
    auth_mode: str = "none"
    credential_ref: Optional[str] = None
    tool_scopes: Tuple[str, ...] = ("health.read", "models.read")
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.gateway_id.strip():
            raise HermesGatewayError("gateway_id is required")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise HermesGatewayError("base_url must be an absolute http(s) URL")
        if self.pinned_version.strip().lower() in {"", "latest", "main", "head"}:
            raise HermesGatewayError("Hermes version must be explicitly pinned")
        if self.deployment not in {"local", "remote"}:
            raise HermesGatewayError("deployment must be local or remote")
        if self.auth_mode not in {"none", "bearer_ref", "bridge_managed"}:
            raise HermesGatewayError("unsupported Hermes auth mode")
        if self.deployment == "local" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise HermesGatewayError("local Hermes deployment must use a loopback host")
        if self.deployment == "remote" and self.auth_mode == "none":
            raise HermesGatewayError("remote Hermes deployment requires explicit auth mode")
        if self.auth_mode == "bearer_ref" and (not self.credential_ref or not self.credential_ref.isidentifier()):
            raise HermesGatewayError("bearer_ref requires an identifier-only credential_ref")
        if self.auth_mode != "bearer_ref" and self.credential_ref is not None:
            raise HermesGatewayError("credential_ref is only valid with bearer_ref")
        if len(set(self.tool_scopes)) != len(self.tool_scopes):
            raise HermesGatewayError("duplicate Hermes tool scope")
        for scope in self.tool_scopes:
            if scope not in HERMES_SUPPORTED_SCOPES or scope.startswith(HERMES_FORBIDDEN_SCOPE_PREFIXES):
                raise HermesGatewayError("unsupported or unsafe Hermes tool scope: %s" % scope)

    def public_metadata(self) -> Mapping[str, object]:
        """Return metadata safe for UI display; credential values never enter it."""
        parsed = urlparse(self.base_url)
        return {
            "gateway_id": self.gateway_id,
            "provider": "hermes_webui",
            "deployment": self.deployment,
            "host": parsed.hostname,
            "port": parsed.port,
            "pinned_version": self.pinned_version,
            "auth_mode": self.auth_mode,
            "credential_ref": self.credential_ref,
            "tool_scopes": list(self.tool_scopes),
            "enabled": self.enabled,
        }

    def bridge_candidate(self, timeout_seconds: float = 0.75) -> BridgeCandidate:
        return BridgeCandidate(self.gateway_id, "hermes_webui", self.base_url, timeout_seconds)


class HermesGatewayAdapter:
    """Validated declaration wrapper with no network or execution side effects."""

    def __init__(self, config: HermesGatewayConfig):
        self.config = config

    def status(self) -> str:
        return "ready" if self.config.enabled else "unavailable"

    def capability_metadata(self) -> Mapping[str, object]:
        return {"tools": "tools.invoke" in self.config.tool_scopes, "tool_scopes": list(self.config.tool_scopes), "deployment": self.config.deployment, "pinned_version": self.config.pinned_version}


__all__ = ["HERMES_FORBIDDEN_SCOPE_PREFIXES", "HERMES_SUPPORTED_SCOPES", "HermesGatewayAdapter", "HermesGatewayConfig", "HermesGatewayError"]
