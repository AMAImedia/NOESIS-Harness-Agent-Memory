"""Version-pinned declarative DeepSeek Harness bridge for NOESIS.

Patterns are borrowed from deepseek-harness plugin contracts, Hermes bridge
capability discovery, and NOESIS fail-soft provider selection. The adapter
only validates declarations and maps plugin capabilities; it never contacts a
remote endpoint, stores credentials, or executes generated output.
"""

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence, Tuple
from urllib.parse import urlparse

from .bridge_discovery import BridgeCandidate
from .provider_registry import CAPABILITY_KEYS

DEEPSEEK_SUPPORTED_PLUGIN_CAPABILITIES = frozenset(CAPABILITY_KEYS)


class DeepSeekHarnessError(ValueError):
    """Raised for invalid DeepSeek Harness declarations."""


@dataclass(frozen=True)
class CompatibilityResult:
    status: str
    reason: str
    supported: Tuple[str, ...] = ()
    missing: Tuple[str, ...] = ()


@dataclass(frozen=True)
class DeepSeekHarnessConfig:
    harness_id: str
    base_url: str
    pinned_version: str
    plugin_id: str
    plugin_version: str
    deployment: str = "local"
    auth_mode: str = "none"
    credential_ref: Optional[str] = None
    plugin_capabilities: Mapping[str, Tuple[str, ...]] = ()
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.harness_id.strip() or not self.plugin_id.strip():
            raise DeepSeekHarnessError("harness_id and plugin_id are required")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise DeepSeekHarnessError("base_url must be an absolute http(s) URL")
        for name, value in (("pinned_version", self.pinned_version), ("plugin_version", self.plugin_version)):
            if value.strip().lower() in {"", "latest", "main", "head"}:
                raise DeepSeekHarnessError("%s must be explicitly pinned" % name)
        if self.deployment not in {"local", "remote"}:
            raise DeepSeekHarnessError("deployment must be local or remote")
        if self.auth_mode not in {"none", "bearer_ref", "bridge_managed"}:
            raise DeepSeekHarnessError("unsupported DeepSeek Harness auth mode")
        if self.deployment == "local" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise DeepSeekHarnessError("local DeepSeek Harness must use a loopback host")
        if self.deployment == "remote" and self.auth_mode == "none":
            raise DeepSeekHarnessError("remote DeepSeek Harness requires explicit auth mode")
        if self.auth_mode == "bearer_ref" and (not self.credential_ref or not self.credential_ref.isidentifier()):
            raise DeepSeekHarnessError("bearer_ref requires an identifier-only credential_ref")
        if self.auth_mode != "bearer_ref" and self.credential_ref is not None:
            raise DeepSeekHarnessError("credential_ref is only valid with bearer_ref")
        for plugin_name, capabilities in dict(self.plugin_capabilities).items():
            if not str(plugin_name).strip():
                raise DeepSeekHarnessError("plugin name is required")
            for capability in capabilities:
                if capability not in DEEPSEEK_SUPPORTED_PLUGIN_CAPABILITIES:
                    raise DeepSeekHarnessError("unsupported plugin capability: %s" % capability)

    def public_metadata(self) -> Mapping[str, object]:
        parsed = urlparse(self.base_url)
        return {
            "harness_id": self.harness_id,
            "provider": "deepseek_harness",
            "deployment": self.deployment,
            "host": parsed.hostname,
            "port": parsed.port,
            "pinned_version": self.pinned_version,
            "plugin_id": self.plugin_id,
            "plugin_version": self.plugin_version,
            "auth_mode": self.auth_mode,
            "credential_ref": self.credential_ref,
            "plugin_capabilities": {name: list(values) for name, values in self.plugin_capabilities.items()},
            "enabled": self.enabled,
        }

    def bridge_candidate(self, timeout_seconds: float = 0.75) -> BridgeCandidate:
        return BridgeCandidate(self.harness_id, "deepseek_harness", self.base_url, timeout_seconds)


class DeepSeekHarnessAdapter:
    """Declarative DeepSeek Harness wrapper with deterministic compatibility checks."""

    def __init__(self, config: DeepSeekHarnessConfig):
        self.config = config

    def status(self) -> str:
        return "ready" if self.config.enabled else "unavailable"

    def capability_mapping(self) -> Mapping[str, Tuple[str, ...]]:
        result = {capability: [] for capability in sorted(DEEPSEEK_SUPPORTED_PLUGIN_CAPABILITIES)}
        for plugin_name, capabilities in self.config.plugin_capabilities.items():
            for capability in capabilities:
                result[capability].append(plugin_name)
        return {key: tuple(value) for key, value in result.items()}

    def compatibility(self, required_capabilities: Sequence[str], contract_version: str = "1.0") -> CompatibilityResult:
        if not self.config.enabled:
            return CompatibilityResult("unavailable", "adapter_disabled")
        if contract_version != "1.0":
            return CompatibilityResult("incompatible", "unsupported_contract_version")
        supported = self.capability_mapping()
        required = tuple(dict.fromkeys(required_capabilities))
        unknown = tuple(sorted(set(required) - DEEPSEEK_SUPPORTED_PLUGIN_CAPABILITIES))
        if unknown:
            return CompatibilityResult("incompatible", "unknown_required_capability", (), unknown)
        present = tuple(sorted(capability for capability in required if supported.get(capability)))
        missing = tuple(sorted(set(required) - set(present)))
        if missing:
            return CompatibilityResult("degraded", "missing_plugin_capability", present, missing)
        return CompatibilityResult("ready", "all_required_capabilities_mapped", present, ())


__all__ = ["CompatibilityResult", "DEEPSEEK_SUPPORTED_PLUGIN_CAPABILITIES", "DeepSeekHarnessAdapter", "DeepSeekHarnessConfig", "DeepSeekHarnessError"]
