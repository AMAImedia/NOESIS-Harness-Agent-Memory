"""Verified executable-skill adapter over the bounded child runtime."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Sequence

from .child_execution import ChildExecutionRuntime, ExecutionRequest, ExecutionResult
from .gatekeeper import Gatekeeper
from .skill_manifest import MANIFEST_FILENAME, SkillManifest, SkillManifestError, digest_files
from .skill_store import SkillStore, SkillStoreError


class SkillRuntimeError(ValueError):
    """Raised for invalid skill runtime configuration."""


class ExecutableSkillRuntime:
    """Execute only active, digest-verified skill entrypoints in a child process."""

    def __init__(self, skill_store: SkillStore, child_runtime: ChildExecutionRuntime, gatekeeper: Gatekeeper, *, python_executable: str | None = None, require_hardened_sandbox: bool = True):
        self.skill_store = skill_store
        self.child_runtime = child_runtime
        self.gatekeeper = gatekeeper
        self.python_executable = python_executable or sys.executable
        self.require_hardened_sandbox = bool(require_hardened_sandbox)

    @staticmethod
    def _platform() -> str:
        return "windows" if sys.platform.startswith("win") else "macos" if sys.platform == "darwin" else "linux"

    def _installed_root(self, skill_id: str) -> tuple[Path, SkillManifest]:
        active = self.skill_store.active(skill_id)
        if not active:
            raise SkillRuntimeError("skill_not_active")
        version = str(active.get("version", ""))
        root = self.skill_store.skills_root / skill_id / "versions" / version
        if not root.is_dir():
            raise SkillRuntimeError("active_skill_version_missing")
        try:
            manifest = SkillManifest.from_file(str(root / MANIFEST_FILENAME))
        except (OSError, SkillManifestError) as exc:
            raise SkillRuntimeError("installed_manifest_invalid") from exc
        observed = digest_files(str(root))
        if observed != manifest.digest or observed != str(active.get("digest", "")):
            raise SkillRuntimeError("skill_digest_mismatch")
        if self._platform() not in manifest.platforms and "any" not in manifest.platforms:
            raise SkillRuntimeError("skill_platform_not_supported")
        if not manifest.entrypoint:
            raise SkillRuntimeError("entrypoint_required")
        entrypoint = (root / manifest.entrypoint).resolve()
        try:
            entrypoint.relative_to(root)
        except ValueError as exc:
            raise SkillRuntimeError("entrypoint_escape") from exc
        if entrypoint.is_symlink() or not entrypoint.is_file():
            raise SkillRuntimeError("entrypoint_missing_or_symlink")
        if self.require_hardened_sandbox:
            promotion_receipt = root / "PROMOTION_RECEIPT.json"
            if promotion_receipt.is_symlink() or not promotion_receipt.is_file():
                raise SkillRuntimeError("promotion_receipt_required")
        return root, manifest

    @staticmethod
    def _copy_bundle(source: Path, target: Path) -> None:
        for item in sorted(source.rglob("*")):
            relative = item.relative_to(source)
            destination = target / relative
            if item.is_symlink():
                raise SkillRuntimeError("symlink_in_installed_skill")
            if item.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            elif item.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(item), str(destination))

    def run(self, skill_id: str, request_id: str, *, arguments: Sequence[str] = ()) -> ExecutionResult:
        decision = self.gatekeeper.get(request_id)
        if not decision or decision.get("status") != "committed":
            return ExecutionResult("denied", request_id, None, "", "", 0.0, "gatekeeper_commit_required")
        if decision.get("capability") != "skill.execute" or decision.get("target") != skill_id:
            return ExecutionResult("denied", request_id, None, "", "", 0.0, "skill_capability_target_mismatch")
        if len(arguments) > 32 or any(not isinstance(item, str) or len(item) > 1024 for item in arguments):
            return ExecutionResult("denied", request_id, None, "", "", 0.0, "skill_arguments_out_of_bounds")
        if self.require_hardened_sandbox and self.child_runtime.sandbox_backend is None:
            return ExecutionResult("denied", request_id, None, "", "", 0.0, "skill_requires_hardened_sandbox")
        try:
            installed, manifest = self._installed_root(skill_id)
        except (SkillRuntimeError, SkillStoreError) as exc:
            return ExecutionResult("denied", request_id, None, "", "", 0.0, str(exc))
        try:
            with tempfile.TemporaryDirectory(prefix="noesis-skill-", dir=str(self.skill_store.root)) as temp:
                workspace = Path(temp)
                bundle = workspace / ".skill"
                self._copy_bundle(installed, bundle)
                request = ExecutionRequest(request_id, (self.python_executable, ".skill/" + manifest.entrypoint, *tuple(arguments)), str(workspace), (Path(self.python_executable).name,), timeout_seconds=30.0, network=False, skill_id=skill_id, manifest=manifest if self.require_hardened_sandbox else None, granted_capabilities=("skill.execute",) if self.require_hardened_sandbox else ())
                return self.child_runtime.run(request)
        except (OSError, SkillRuntimeError) as exc:
            return ExecutionResult("failed", request_id, None, "", "", 0.0, "skill_staging_failed:%s" % type(exc).__name__)


__all__ = ["ExecutableSkillRuntime", "SkillRuntimeError"]
