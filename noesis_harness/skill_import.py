"""Safe staged import pipeline for `.noesisskill` bundles.

Patterns are borrowed from package staging, content-addressed verification,
Hermes/DeepSeek plugin boundaries, and NOESIS deny-by-default execution rules.
The pipeline copies and scans data only; it never imports Python modules,
executes entrypoints, follows symlinks, or invokes model-generated code.
"""

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple

from .skill_manifest import MANIFEST_FILENAME, SkillManifest, SkillManifestError, digest_files


class SkillImportError(ValueError):
    """Raised when a skill bundle cannot pass the safe import gate."""


@dataclass(frozen=True)
class ImportAssessment:
    status: str
    reason: str
    source: str
    manifest_digest: Optional[str] = None
    observed_digest: Optional[str] = None
    file_count: int = 0
    total_bytes: int = 0
    staging_path: Optional[str] = None


class SafeSkillImport:
    """Stage and scan a skill bundle without executing any skill content."""

    def __init__(self, staging_root: str, *, max_files: int = 256, max_bytes: int = 32 * 1024 * 1024):
        if max_files < 1 or max_bytes < 1:
            raise SkillImportError("import limits must be positive")
        self.staging_root = Path(staging_root).expanduser().resolve()
        self.max_files = int(max_files)
        self.max_bytes = int(max_bytes)

    def _scan_tree(self, root: Path) -> Tuple[int, int]:
        count = 0
        total = 0
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise SkillImportError("symlink_detected")
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if relative.startswith("../") or "/../" in relative or relative == "..":
                raise SkillImportError("path_traversal_detected")
            count += 1
            total += path.stat().st_size
            if count > self.max_files:
                raise SkillImportError("file_limit_exceeded")
            if total > self.max_bytes:
                raise SkillImportError("byte_limit_exceeded")
        return count, total

    def scan(self, source: str) -> ImportAssessment:
        root = Path(source).expanduser().resolve()
        try:
            if not root.is_dir():
                raise SkillImportError("source_not_directory")
            count, total = self._scan_tree(root)
            manifest_path = root / MANIFEST_FILENAME
            if not manifest_path.is_file() or manifest_path.is_symlink():
                raise SkillImportError("manifest_missing")
            manifest = SkillManifest.from_file(str(manifest_path))
            observed = digest_files(str(root))
            if observed != manifest.digest:
                return ImportAssessment("rejected", "digest_mismatch", str(root), manifest.digest, observed, count, total)
            return ImportAssessment("scanned", "digest_verified", str(root), manifest.digest, observed, count, total)
        except (OSError, SkillManifestError, SkillImportError) as exc:
            return ImportAssessment("rejected", str(exc), str(root))

    def stage(self, source: str) -> ImportAssessment:
        assessment = self.scan(source)
        if assessment.status != "scanned":
            return assessment
        source_root = Path(source).expanduser().resolve()
        self.staging_root.mkdir(parents=True, exist_ok=True)
        destination = Path(tempfile.mkdtemp(prefix="skill_", dir=str(self.staging_root)))
        try:
            for path in sorted(source_root.rglob("*")):
                relative = path.relative_to(source_root)
                target = destination / relative
                if path.is_symlink():
                    raise SkillImportError("symlink_detected")
                if path.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                elif path.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(str(path), str(target))
            return ImportAssessment("staged", "scan_verified", str(source_root), assessment.manifest_digest, assessment.observed_digest, assessment.file_count, assessment.total_bytes, str(destination))
        except (OSError, SkillImportError) as exc:
            return ImportAssessment("rejected", str(exc), str(source_root), staging_path=str(destination))

    def approve(self, assessment: ImportAssessment, test_hook: Optional[Callable[[str], bool]] = None) -> ImportAssessment:
        if assessment.status != "staged" or not assessment.staging_path:
            return ImportAssessment("rejected", "stage_required", assessment.source, assessment.manifest_digest, assessment.observed_digest, assessment.file_count, assessment.total_bytes, assessment.staging_path)
        if test_hook is not None:
            try:
                passed = bool(test_hook(assessment.staging_path))
            except Exception:
                passed = False
            if not passed:
                return ImportAssessment("rejected", "test_hook_failed", assessment.source, assessment.manifest_digest, assessment.observed_digest, assessment.file_count, assessment.total_bytes, assessment.staging_path)
        marker = Path(assessment.staging_path) / ".approved"
        marker.write_text(json.dumps({"status": "approved", "digest": assessment.observed_digest}, sort_keys=True) + "\n", encoding="utf-8")
        return ImportAssessment("approved", "verified_and_tested", assessment.source, assessment.manifest_digest, assessment.observed_digest, assessment.file_count, assessment.total_bytes, assessment.staging_path)


__all__ = ["ImportAssessment", "SafeSkillImport", "SkillImportError"]
