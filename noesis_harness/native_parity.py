"""Fail-closed preparation contract for native Windows/macOS parity evidence."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from dataclasses import dataclass
from typing import Any, Mapping


NATIVE_PARITY_SCHEMA = "noesis.native-parity-evidence.v1"


@dataclass(frozen=True)
class NativeParityEvidence:
    target: str
    status: str
    reason: str
    platform: str
    python_version: str
    environment_digest: str
    execution_claim: bool = False

    def to_mapping(self) -> Mapping[str, Any]:
        return {"schema_version": NATIVE_PARITY_SCHEMA, "target": self.target, "status": self.status, "reason": self.reason, "platform": self.platform, "python_version": self.python_version, "environment_digest": self.environment_digest, "execution_claim": self.execution_claim}


def _target_matches(target: str, current_platform: str) -> bool:
    return (target == "windows" and current_platform.startswith("win")) or (target == "macos" and current_platform == "darwin")


def prepare_native_evidence(target: str, *, current_platform: str | None = None, python_version: tuple[int, int, int] | None = None) -> NativeParityEvidence:
    if target not in {"windows", "macos"}:
        raise ValueError("unsupported_native_target")
    current_platform = current_platform or sys.platform
    python_version = python_version or sys.version_info[:3]
    version_text = ".".join(str(value) for value in python_version)
    identity = {"target": target, "platform": current_platform, "python_version": version_text, "machine": platform.machine(), "system": platform.system()}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    if not _target_matches(target, current_platform):
        return NativeParityEvidence(target, "not_run", "target_host_or_python_mismatch", current_platform, version_text, digest)
    if tuple(python_version[:2]) != (3, 14):
        return NativeParityEvidence(target, "not_run", "target_host_or_python_mismatch", current_platform, version_text, digest)
    return NativeParityEvidence(target, "not_run", "parity_contract_not_executed", current_platform, version_text, digest)


def operator_bundle(target: str) -> Mapping[str, Any]:
    if target not in {"windows", "macos"}:
        raise ValueError("unsupported_native_target")
    command = "pwsh -NoProfile -File scripts/run_native_parity.ps1" if target == "windows" else "zsh scripts/run_native_parity_macos.sh"
    return {"schema_version": NATIVE_PARITY_SCHEMA, "target": target, "required_python": "3.14.x", "command": command, "network_allowed": False, "credentials_required": False, "required_artifacts": ["environment.json", "parity-results.json", "sha256sums.txt", "sbom.json"], "status_rule": "not_run_is_not_passed"}


__all__ = ["NATIVE_PARITY_SCHEMA", "NativeParityEvidence", "prepare_native_evidence", "operator_bundle"]
