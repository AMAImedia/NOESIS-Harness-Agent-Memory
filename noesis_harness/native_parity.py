"""Fail-closed preparation contract for native Windows/macOS parity evidence."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_digests(text: str) -> dict[str, str]:
    try:
        parsed = json.loads(text)
        entries = parsed if isinstance(parsed, list) else [parsed]
        result = {}
        for entry in entries:
            if isinstance(entry, dict) and entry.get("Hash") and entry.get("Path"):
                result[Path(str(entry["Path"])).name] = str(entry["Hash"]).lower()
        if result:
            return result
    except (ValueError, TypeError):
        pass
    result = {}
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and len(parts[0]) == 64:
            result[Path(parts[-1].lstrip("*\\")).name] = parts[0].lower()
    return result


def validate_native_artifacts(target: str, evidence_dir: str | Path, *, current_platform: str | None = None, python_version: tuple[int, int, int] | None = None) -> NativeParityEvidence:
    """Validate operator-produced artifacts without manufacturing native execution evidence."""
    if target not in {"windows", "macos"}:
        raise ValueError("unsupported_native_target")
    current_platform = current_platform or sys.platform
    python_version = python_version or sys.version_info[:3]
    prepared = prepare_native_evidence(target, current_platform=current_platform, python_version=python_version)
    if prepared.reason == "target_host_or_python_mismatch":
        return prepared
    root = Path(evidence_dir)
    required = ("environment.json", "parity-results.json", "sha256sums.txt", "sbom.json")
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        return NativeParityEvidence(target, "blocked", "missing_required_artifact:" + ",".join(missing), current_platform, prepared.python_version, prepared.environment_digest)
    try:
        environment = json.loads((root / "environment.json").read_text(encoding="utf-8"))
        parity = json.loads((root / "parity-results.json").read_text(encoding="utf-8"))
        sbom = json.loads((root / "sbom.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return NativeParityEvidence(target, "blocked", "malformed_required_artifact", current_platform, prepared.python_version, prepared.environment_digest)
    if environment.get("target") != target or environment.get("network_allowed") is not False or environment.get("credentials_available") is not False:
        return NativeParityEvidence(target, "blocked", "environment_guard_failed", current_platform, prepared.python_version, prepared.environment_digest)
    if parity.get("target") != target or parity.get("status") != "passed" or parity.get("execution_claim") is not True:
        return NativeParityEvidence(target, "blocked", "parity_result_not_passed", current_platform, prepared.python_version, prepared.environment_digest)
    files = sbom.get("files")
    if not isinstance(files, list) or not set(required[:3]).issubset(set(files)):
        return NativeParityEvidence(target, "blocked", "sbom_missing_required_files", current_platform, prepared.python_version, prepared.environment_digest)
    manifest_text = (root / "sha256sums.txt").read_text(encoding="utf-8")
    manifest = _manifest_digests(manifest_text)
    if not manifest:
        return NativeParityEvidence(target, "blocked", "sha256_manifest_empty", current_platform, prepared.python_version, prepared.environment_digest)
    for name in ("environment.json", "parity-results.json"):
        if manifest.get(name) != _sha256(root / name):
            return NativeParityEvidence(target, "blocked", "sha256_manifest_mismatch:" + name, current_platform, prepared.python_version, prepared.environment_digest)
    return NativeParityEvidence(target, "passed", "matching_host_python_and_validated_artifacts", current_platform, prepared.python_version, prepared.environment_digest, True)


def operator_bundle(target: str) -> Mapping[str, Any]:
    if target not in {"windows", "macos"}:
        raise ValueError("unsupported_native_target")
    command = "pwsh -NoProfile -File scripts/run_native_parity.ps1" if target == "windows" else "zsh scripts/run_native_parity_macos.sh"
    return {"schema_version": NATIVE_PARITY_SCHEMA, "target": target, "required_python": "3.14.x", "command": command, "validator": "validate_native_artifacts", "network_allowed": False, "credentials_required": False, "required_artifacts": ["environment.json", "parity-results.json", "sha256sums.txt", "sbom.json"], "integrity_rule": "environment_and_parity_sha256_must_match_manifest", "status_rule": "not_run_is_not_passed"}


__all__ = ["NATIVE_PARITY_SCHEMA", "NativeParityEvidence", "prepare_native_evidence", "validate_native_artifacts", "operator_bundle"]
