"""Declarative Hermes/DeepSeek metadata translator for NOESIS.

Patterns are borrowed from versioned adapter schemas, plugin capability
registries, and NOESIS deny-by-default import boundaries. The translator only
normalizes public metadata into validated adapter declarations; it never
imports presets, executes commands, starts bridges, or resolves credentials.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Tuple

from .deepseek_harness import DeepSeekHarnessConfig
from .hermes_gateway import HermesGatewayConfig


class MetadataTranslationError(ValueError):
    """Raised when foreign metadata cannot be safely translated."""


_FORBIDDEN_KEYS = frozenset({"command", "commands", "exec", "execute", "entrypoint", "preset", "presets", "workflow", "system_prompt", "actions", "api_key", "token", "secret", "password", "authorization"})
_ALLOWED_COMMON = frozenset({"id", "name", "gateway_id", "harness_id", "base_url", "endpoint", "version", "pinned_version", "deployment", "auth_mode", "credential_ref", "enabled", "tool_scopes", "capabilities", "plugin_id", "plugin_version", "plugin_capabilities"})


@dataclass(frozen=True)
class TranslationResult:
    status: str
    source_kind: str
    metadata: Mapping[str, Any]
    dropped_fields: Tuple[str, ...] = ()
    reason: str = "translated"


def _key_guard(metadata: Mapping[str, Any]) -> None:
    for key, value in metadata.items():
        normalized = str(key).lower().replace("-", "_").replace(" ", "_")
        if normalized in _FORBIDDEN_KEYS or any(part in normalized for part in ("token", "secret", "password", "api_key", "authorization")):
            raise MetadataTranslationError("unsafe foreign metadata field: %s" % key)
        if isinstance(value, Mapping) and normalized not in {"plugin_capabilities", "capabilities"}:
            _key_guard(value)


def _base(metadata: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "base_url": metadata.get("base_url", metadata.get("endpoint")),
        "pinned_version": metadata.get("pinned_version", metadata.get("version")),
        "deployment": metadata.get("deployment", "local"),
        "auth_mode": metadata.get("auth_mode", "none"),
        "credential_ref": metadata.get("credential_ref"),
        "enabled": bool(metadata.get("enabled", False)),
    }


def translate_metadata(source_kind: str, metadata: Mapping[str, Any]) -> TranslationResult:
    """Translate only whitelisted metadata; no foreign executable semantics survive."""
    if source_kind not in {"hermes_webui", "deepseek_harness"}:
        raise MetadataTranslationError("unsupported source kind")
    if not isinstance(metadata, Mapping):
        raise MetadataTranslationError("metadata must be an object")
    _key_guard(metadata)
    forbidden_presets = sorted(set(str(key) for key in metadata) & _FORBIDDEN_KEYS)
    if forbidden_presets:
        raise MetadataTranslationError("foreign preset/execution metadata is forbidden")
    unknown = tuple(sorted(str(key) for key in metadata if str(key) not in _ALLOWED_COMMON))
    if source_kind == "hermes_webui":
        values = dict(_base(metadata))
        values["gateway_id"] = str(metadata.get("gateway_id", metadata.get("id", metadata.get("name", "hermes-translated"))))
        values["tool_scopes"] = tuple(str(item) for item in metadata.get("tool_scopes", metadata.get("capabilities", ("health.read", "models.read"))))
        config = HermesGatewayConfig(**values)
        return TranslationResult("translated", source_kind, config.public_metadata(), unknown)
    values = dict(_base(metadata))
    values["harness_id"] = str(metadata.get("harness_id", metadata.get("id", metadata.get("name", "deepseek-translated"))))
    values["plugin_id"] = str(metadata.get("plugin_id", "translated-plugin"))
    values["plugin_version"] = str(metadata.get("plugin_version", metadata.get("version", "1.0.0")))
    raw_plugins = metadata.get("plugin_capabilities", {})
    values["plugin_capabilities"] = {str(name): tuple(str(capability) for capability in capabilities) for name, capabilities in raw_plugins.items()} if isinstance(raw_plugins, Mapping) else {}
    config = DeepSeekHarnessConfig(**values)
    return TranslationResult("translated", source_kind, config.public_metadata(), unknown)


__all__ = ["MetadataTranslationError", "TranslationResult", "translate_metadata"]
