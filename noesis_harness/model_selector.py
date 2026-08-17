"""Deterministic capability-aware model selection for the NOESIS UI.

Patterns are borrowed from provider capability matrices, fail-soft feature
negotiation, and the NOESIS metadata-only control plane. Selection operates on
validated public records only; it never invokes a model or accesses secrets.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Tuple

from .provider_registry import CAPABILITY_KEYS


@dataclass(frozen=True)
class SelectionResult:
    status: str
    reason: str
    model_id: Optional[str] = None
    provider: Optional[str] = None
    capabilities: Mapping[str, bool] = None
    missing: Tuple[str, ...] = ()


def _record_capabilities(record: Mapping[str, Any]) -> Mapping[str, bool]:
    raw = record.get("capabilities", {})
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): bool(value) for key, value in raw.items() if str(key) in CAPABILITY_KEYS}


def select_model(records: Sequence[Mapping[str, Any]], required_capabilities: Sequence[str] = (), preferred_provider: Optional[str] = None) -> SelectionResult:
    """Select deterministically or explain why a request cannot be served."""
    required = tuple(dict.fromkeys(str(item) for item in required_capabilities))
    unknown = tuple(sorted(set(required) - CAPABILITY_KEYS))
    if unknown:
        return SelectionResult("incompatible", "unknown_required_capability", missing=unknown)
    candidates = []
    for record in records:
        if not isinstance(record, Mapping) or record.get("status") != "ready":
            continue
        model_id = str(record.get("id", ""))
        provider = str(record.get("provider", ""))
        if not model_id or not provider:
            continue
        caps = _record_capabilities(record)
        missing = tuple(sorted(key for key in required if not caps.get(key, False)))
        candidates.append((len(missing), 0 if preferred_provider and provider == preferred_provider else 1, provider, model_id, caps, missing))
    if not candidates:
        return SelectionResult("unavailable", "no_ready_models")
    candidates.sort(key=lambda item: item[:4])
    best = candidates[0]
    if best[0] > 0:
        return SelectionResult("degraded", "required_capabilities_unavailable", best[3], best[2], best[4], best[5])
    return SelectionResult("ready", "capabilities_satisfied", best[3], best[2], best[4], ())


__all__ = ["SelectionResult", "select_model"]
