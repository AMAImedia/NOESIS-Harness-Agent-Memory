"""Safe integration coordinator for Hermes and DeepSeek child runtimes.

Patterns are borrowed from NOESIS BridgeDiscovery, ChildRuntimeSupervisor,
Hermes gateway scopes, and DeepSeek plugin compatibility checks. Registration is
metadata-only; discovery is explicitly opt-in and read-only. The coordinator
never starts a child process, resolves credentials, invokes a model, or invokes
a tool implicitly.
"""

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence, Tuple

from .bridge_discovery import BridgeCandidate, BridgeDiscovery, BridgeStatus
from .deepseek_harness import CompatibilityResult, DeepSeekHarnessAdapter
from .hermes_gateway import HermesGatewayAdapter


@dataclass(frozen=True)
class IntegrationRecord:
    bridge_id: str
    kind: str
    status: str
    metadata: Mapping[str, object]
    candidate: BridgeCandidate


class BridgeIntegrationError(ValueError):
    """Raised when bridge registration violates integration boundaries."""


class BridgeIntegrationCoordinator:
    """Manage optional bridge declarations without implicit runtime side effects."""

    def __init__(self, *, contract_version: str = "1.0"):
        if not contract_version or not isinstance(contract_version, str):
            raise BridgeIntegrationError("contract_version is required")
        self.contract_version = contract_version
        self._records = {}

    def register_hermes(self, adapter: HermesGatewayAdapter, *, timeout_seconds: float = 0.75) -> IntegrationRecord:
        config = adapter.config
        candidate = config.bridge_candidate(timeout_seconds)
        record = IntegrationRecord(config.gateway_id, "hermes_webui", adapter.status(), config.public_metadata(), candidate)
        self._records[record.bridge_id] = record
        return record

    def register_deepseek(self, adapter: DeepSeekHarnessAdapter, *, timeout_seconds: float = 0.75) -> IntegrationRecord:
        config = adapter.config
        candidate = config.bridge_candidate(timeout_seconds)
        record = IntegrationRecord(config.harness_id, "deepseek_harness", adapter.status(), config.public_metadata(), candidate)
        self._records[record.bridge_id] = record
        return record

    def records(self) -> Tuple[IntegrationRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    def discover(self, bridge_ids: Optional[Sequence[str]] = None) -> Tuple[BridgeStatus, ...]:
        selected = set(bridge_ids) if bridge_ids is not None else None
        candidates = tuple(record.candidate for record in self.records() if selected is None or record.bridge_id in selected)
        return BridgeDiscovery(candidates).discover()

    def compatibility(self, bridge_id: str, required_capabilities: Sequence[str] = ()) -> CompatibilityResult:
        record = self._records.get(bridge_id)
        if record is None:
            return CompatibilityResult("unavailable", "bridge_not_registered")
        if record.kind != "deepseek_harness":
            required = tuple(dict.fromkeys(required_capabilities))
            available = tuple(str(item) for item in record.metadata.get("tool_scopes", ()))
            missing = tuple(sorted(set(required) - set(available)))
            return CompatibilityResult("degraded" if missing else "ready", "scope_mapping", tuple(sorted(set(required) - set(missing))), missing)
        return CompatibilityResult("unavailable", "deepseek_adapter_not_attached")

    def metadata(self) -> Tuple[Mapping[str, object], ...]:
        return tuple(record.metadata for record in self.records())


__all__ = ["BridgeIntegrationCoordinator", "BridgeIntegrationError", "IntegrationRecord"]
