"""Build and verify a deterministic source-portable Python 3.14 artifact.

Patterns: reproducible release manifests, SPDX inventory and NOESIS native
claim boundaries. This audit does not build or claim a native Windows/macOS
executable.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from scripts.build_portable_artifact import build
from scripts.verify_portable_artifact import verify


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="noesis-portable-audit-") as directory:
        artifact = Path(directory) / "NOESIS-portable-python314-source.zip"
        build_result = build(str(root), str(artifact))
        verification = verify(str(artifact))
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        evidence = {
            "schema_version": "noesis.portable-artifact-evidence.v2",
            "artifact_kind": "source_portable_python314_zip",
            "file_count": build_result["file_count"],
            "artifact_size": artifact.stat().st_size,
            "artifact_sha256": digest,
            "verification": {
                "status": verification["status"],
                "file_count": verification.get("file_count", 0),
                "errors": verification.get("errors", []),
            },
            "native_claim": False,
            "claim_boundary": "static portable artifact evidence; native Windows/macOS build and execution require matching hosts",
        }
    output = root / "docs" / "PORTABLE_ARTIFACT_EVIDENCE.json"
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, sort_keys=True))
    if verification["status"] != "passed":
        raise SystemExit(2)


if __name__ == "__main__":
    main()


__all__ = ["main"]

