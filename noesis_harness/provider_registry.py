"""Declarative provider/model registry for the NOESIS control plane.

Patterns are borrowed from OpenAI-compatible gateway metadata, Ollama and
llama.cpp local endpoints, vLLM/LM Studio registries, and NOESIS fail-soft
capability contracts. This module stores metadata only: it never calls a
provider, resolves credentials, or executes model output.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple

from .ui_contract import model_payload

SUPPORTED_PROVIDER_KINDS = frozenset({"ollama", "lm_studio", "llama_cpp", "vllm", "openai_compatible", "hermes_webui", "deepseek_harness"})
CAPABILITY_KEYS = frozenset({"tools", "vision", "structured_output", "streaming", "long_context"})
_SECRET_NAMES = frozenset({"token", "secret", "password", "credential", "authorization", "api_key", "api-key", "private_key", "private-key"})


class ProviderRegistryError(ValueError):
    """Raised for invalid declarative provider metadata."""


@dataclass(frozen=True)
class ProviderAdapterSpec:
    kind: str
    endpoint_prefix: str
    health_path: str
    models_path: str
    auth_mode: str
    default_capabilities: Mapping[str, bool]


_ADAPTER_SPECS = {
    "ollama": ProviderAdapterSpec("ollama", "/api", "/api/tags", "/api/tags", "none_or_local", {"tools": False, "vision": False, "structured_output": False, "streaming": True, "long_context": False}),
    "lm_studio": ProviderAdapterSpec("lm_studio", "/v1", "/v1/models", "/v1/models", "optional_bearer", {"tools": False, "vision": False, "structured_output": False, "streaming": True, "long_context": False}),
    "llama_cpp": ProviderAdapterSpec("llama_cpp", "/v1", "/v1/models", "/v1/models", "optional_bearer", {"tools": False, "vision": False, "structured_output": False, "streaming": True, "long_context": False}),
    "vllm": ProviderAdapterSpec("vllm", "/v1", "/v1/models", "/v1/models", "optional_bearer", {"tools": False, "vision": False, "structured_output": False, "streaming": True, "long_context": False}),
    "openai_compatible": ProviderAdapterSpec("openai_compatible", "/v1", "/v1/models", "/v1/models", "required_external_auth", {"tools": False, "vision": False, "structured_output": False, "streaming": True, "long_context": False}),
    "hermes_webui": ProviderAdapterSpec("hermes_webui", "", "/health", "/models", "bridge_managed", {"tools": True, "vision": False, "structured_output": True, "streaming": True, "long_context": True}),
    "deepseek_harness": ProviderAdapterSpec("deepseek_harness", "", "/health", "/models", "bridge_managed", {"tools": True, "vision": False, "structured_output": True, "streaming": True, "long_context": True}),
}


def adapter_spec(provider_kind: str) -> ProviderAdapterSpec:
    """Return static adapter metadata; no endpoint is contacted."""
    try:
        return _ADAPTER_SPECS[provider_kind]
    except KeyError:
        raise ProviderRegistryError("unsupported provider kind: %s" % provider_kind)


@dataclass(frozen=True)
class ModelDescriptor:
    model_id: str
    provider: str
    endpoint_kind: str = "unknown"
    status: str = "ready"
    capabilities: Mapping[str, bool] = ()

    def to_record(self) -> dict[str, Any]:
        if not self.model_id or not self.provider:
            raise ProviderRegistryError("model_id and provider are required")
        if self.provider not in SUPPORTED_PROVIDER_KINDS:
            raise ProviderRegistryError("unsupported provider kind: %s" % self.provider)
        if self.status not in {"ready", "degraded", "unavailable"}:
            raise ProviderRegistryError("model status must be ready, degraded or unavailable")
        caps = dict(self.capabilities)
        unknown = sorted(set(str(key) for key in caps) - CAPABILITY_KEYS)
        if unknown:
            raise ProviderRegistryError("unsupported capability key: %s" % unknown[0])
        return {"id": self.model_id, "provider": self.provider, "endpoint_kind": self.endpoint_kind, "status": self.status, "capabilities": {str(key): bool(value) for key, value in caps.items()}}


@dataclass(frozen=True)
class ProviderDescriptor:
    provider_id: str
    kind: str
    status: str = "unavailable"
    models: Tuple[ModelDescriptor, ...] = ()
    endpoint_kind: str = "unknown"

    def __post_init__(self) -> None:
        if not self.provider_id:
            raise ProviderRegistryError("provider_id is required")
        if self.kind not in SUPPORTED_PROVIDER_KINDS:
            raise ProviderRegistryError("unsupported provider kind: %s" % self.kind)
        if self.status not in {"ready", "degraded", "unavailable"}:
            raise ProviderRegistryError("provider status must be ready, degraded or unavailable")
        for model in self.models:
            if model.provider != self.kind:
                raise ProviderRegistryError("model provider must match provider kind")

    def records(self) -> Tuple[dict[str, Any], ...]:
        return tuple(model.to_record() for model in self.models)


class ProviderRegistry:
    """In-memory metadata registry; it never stores credentials or calls providers."""

    def __init__(self, providers: Tuple[ProviderDescriptor, ...] = ()):
        self._providers: dict[str, ProviderDescriptor] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: ProviderDescriptor) -> None:
        if provider.provider_id in self._providers:
            raise ProviderRegistryError("duplicate provider_id: %s" % provider.provider_id)
        self._providers[provider.provider_id] = provider

    def descriptors(self) -> Tuple[ProviderDescriptor, ...]:
        return tuple(self._providers[key] for key in sorted(self._providers))

    def records(self) -> Tuple[dict[str, Any], ...]:
        records = []
        for provider in self.descriptors():
            records.extend(provider.records())
        return tuple(sorted(records, key=lambda record: (record["provider"], record["id"])))

    def capability_matrix(self) -> Mapping[str, Mapping[str, bool]]:
        return {kind: dict(adapter_spec(kind).default_capabilities) for kind in sorted(SUPPORTED_PROVIDER_KINDS)}

    def envelope(self):
        records = self.records()
        if not self._providers or not records:
            return model_payload((), provider_registry_status="unavailable", unavailable_reasons=("no_verified_provider_models",))
        status = "ready" if all(provider.status == "ready" for provider in self.descriptors()) else "degraded"
        reasons = tuple("%s:%s" % (provider.provider_id, provider.status) for provider in self.descriptors() if provider.status != "ready")
        return model_payload(records, provider_registry_status=status, unavailable_reasons=reasons)

    @staticmethod
    def validate_public_metadata(metadata: Mapping[str, Any]) -> None:
        for key in metadata:
            normalized = str(key).lower().replace(" ", "_")
            if normalized in _SECRET_NAMES or any(part in normalized for part in ("token", "secret", "password", "credential", "authorization")):
                raise ProviderRegistryError("secret-shaped metadata key is forbidden: %s" % key)
        for value in metadata.values():
            if isinstance(value, Mapping):
                ProviderRegistry.validate_public_metadata(value)


__all__ = ["CAPABILITY_KEYS", "ModelDescriptor", "ProviderAdapterSpec", "ProviderDescriptor", "ProviderRegistry", "ProviderRegistryError", "SUPPORTED_PROVIDER_KINDS", "adapter_spec"]
