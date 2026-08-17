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
    manifest = {"schema_version": "noesis.portable-artifact.v1", "runtime": "python-3.14-only", "created_by": "scripts/build_portable_artifact.py", "files": entries}
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(source).as_posix())
        archive.writestr("PORTABLE_MANIFEST.json", json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return {"output": str(target), "file_count": len(entries), "manifest": manifest}


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
