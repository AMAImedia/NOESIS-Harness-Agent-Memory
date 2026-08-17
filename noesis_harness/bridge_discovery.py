"""Capability-aware discovery for Hermes WebUI and DeepSeek Harness bridges.

Patterns are borrowed from the NOESIS control-plane contract, Hermes capability
advertising, and deepseek-harness readiness probing; probes are read-only and
fail soft by design.
"""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Tuple

from .ui_contract import CONTRACT_VERSION


@dataclass(frozen=True)
class BridgeCandidate:
    bridge_id: str
    kind: str
    base_url: str
    timeout_seconds: float = 0.75


@dataclass(frozen=True)
class BridgeStatus:
    bridge_id: str
    kind: str
    status: str
    reason: str
    contract_version: Optional[str] = None
    model_count: int = 0
    capabilities: Optional[Mapping[str, str]] = None


class BridgeDiscovery:
    """Read-only HTTP probes; never sends credentials or starts a runtime."""

    def __init__(self, candidates: Sequence[BridgeCandidate] = ()):
        self.candidates = tuple(candidates)

    @staticmethod
    def _get_json(url: str, timeout: float) -> Mapping[str, Any]:
        request = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise RuntimeError(f"http_status_{response.status}")
            payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError("response_not_object")
            return payload

    def probe(self, candidate: BridgeCandidate) -> BridgeStatus:
        base = candidate.base_url.rstrip("/")
        try:
            health = self._get_json(f"{base}/health", candidate.timeout_seconds)
            models = self._get_json(f"{base}/models", candidate.timeout_seconds)
            version = health.get("contract_version")
            if version != CONTRACT_VERSION or models.get("contract_version") != CONTRACT_VERSION:
                return BridgeStatus(candidate.bridge_id, candidate.kind, "incompatible", "contract_version_mismatch", str(version), 0, {})
            health_caps = health.get("capabilities", {})
            capability = str(health_caps.get(candidate.kind, "unavailable")) if isinstance(health_caps, Mapping) else "unavailable"
            model_data = models.get("data", {})
            records = model_data.get("models", []) if isinstance(model_data, Mapping) else []
            if not isinstance(records, list):
                return BridgeStatus(candidate.bridge_id, candidate.kind, "incompatible", "models_not_list", str(version), 0, {})
            if capability == "unavailable":
                return BridgeStatus(candidate.bridge_id, candidate.kind, "unavailable", "capability_unavailable", str(version), len(records), {candidate.kind: capability})
            if capability not in {"ready", "degraded"}:
                return BridgeStatus(candidate.bridge_id, candidate.kind, "incompatible", "unknown_capability_status", str(version), len(records), {candidate.kind: capability})
            matching = sum(1 for record in records if isinstance(record, Mapping) and record.get("provider") == candidate.kind)
            if capability == "ready" and matching == 0:
                return BridgeStatus(candidate.bridge_id, candidate.kind, "degraded", "capability_ready_but_no_matching_models", str(version), len(records), {candidate.kind: capability})
            return BridgeStatus(candidate.bridge_id, candidate.kind, capability, "verified", str(version), matching, {candidate.kind: capability})
        except urllib.error.HTTPError as exc:
            try:
                exc.read()
            finally:
                exc.close()
            return BridgeStatus(candidate.bridge_id, candidate.kind, "unavailable", f"probe_failed:{type(exc).__name__}", None, 0, {})
        except (OSError, urllib.error.URLError, TimeoutError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            return BridgeStatus(candidate.bridge_id, candidate.kind, "unavailable", f"probe_failed:{type(exc).__name__}", None, 0, {})

    def discover(self) -> Tuple[BridgeStatus, ...]:
        return tuple(self.probe(candidate) for candidate in self.candidates)


__all__ = ["BridgeCandidate", "BridgeDiscovery", "BridgeStatus"]
