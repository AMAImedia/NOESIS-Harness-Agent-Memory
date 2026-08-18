#!/usr/bin/env python3
"""Build a reproducible source-portable NOESIS artifact with a SHA-256 manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import zipfile
from pathlib import Path

EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".venv", "venv", "models", "secrets"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".pem", ".key"}


def should_include(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if path.is_symlink() or not path.is_file() or path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return relative.as_posix() not in {".env", ".env.local"}


def build_sbom(entries: list[dict]) -> dict:
    """Create a deterministic SPDX 2.3 file inventory for the artifact."""
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    namespace = "https://noesis.local/spdx/" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    files = []
    for index, entry in enumerate(entries, start=1):
        files.append({
            "SPDXID": "SPDXRef-File-%06d" % index,
            "fileName": entry["path"],
            "checksums": [{"algorithm": "SHA256", "checksumValue": entry["sha256"]}],
            "licenseConcluded": "NOASSERTION",
        })
    return {
        "spdxVersion": "SPDX-2.3",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "NOESIS-Harness-Agent-Memory portable artifact",
        "documentNamespace": namespace,
        "creationInfo": {"created": "1970-01-01T00:00:00Z", "creators": ["Tool: NOESIS build_portable_artifact.py"]},
        "dataLicense": "CC0-1.0",
        "files": files,
    }


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def build(root: str, output: str) -> dict:
    source = Path(root).expanduser().resolve()
    target = Path(output).expanduser().resolve()
    if not source.is_dir():
        raise ValueError("project root must be a directory")
    files = sorted(path for path in source.rglob("*") if should_include(path, source))
    entries = []
    for path in files:
        data = path.read_bytes()
        entries.append({"path": path.relative_to(source).as_posix(), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {"schema_version": "noesis.portable-artifact.v1", "runtime": "python-3.14-only", "created_by": "scripts/build_portable_artifact.py", "files": entries, "sbom": {"format": "SPDX-2.3", "path": "PORTABLE_SBOM.spdx.json"}}
    sbom = build_sbom(entries)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            name = path.relative_to(source).as_posix()
            archive.writestr(_zip_info(name), path.read_bytes())
        archive.writestr(_zip_info("PORTABLE_MANIFEST.json"), json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        archive.writestr(_zip_info("PORTABLE_SBOM.spdx.json"), json.dumps(sbom, sort_keys=True, indent=2) + "\n")
    return {"output": str(target), "file_count": len(entries), "manifest": manifest, "sbom": sbom}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build NOESIS source-portable artifact")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    result = build(args.root, args.output)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
