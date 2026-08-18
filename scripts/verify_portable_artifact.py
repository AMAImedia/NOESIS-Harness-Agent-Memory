"""Verify NOESIS portable ZIP manifest and SPDX SBOM consistency."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

METADATA_FILES = {"PORTABLE_MANIFEST.json", "PORTABLE_SBOM.spdx.json"}


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(artifact: str) -> dict[str, Any]:
    path = Path(artifact).expanduser().resolve()
    report: dict[str, Any] = {
        "schema_version": "noesis.portable-artifact-evidence.v1",
        "artifact": str(path),
        "artifact_exists": path.is_file(),
        "status": "failed",
        "errors": [],
    }
    if not path.is_file():
        report["errors"] = ["artifact_missing"]
        return report
    try:
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            if not METADATA_FILES.issubset(names):
                report["errors"] = ["metadata_missing"]
                return report
            manifest = json.loads(archive.read("PORTABLE_MANIFEST.json"))
            sbom = json.loads(archive.read("PORTABLE_SBOM.spdx.json"))
            errors: list[str] = []
            if manifest.get("schema_version") != "noesis.portable-artifact.v1":
                errors.append("manifest_schema")
            if manifest.get("runtime") != "python-3.14-only":
                errors.append("manifest_runtime")
            if sbom.get("spdxVersion") != "SPDX-2.3":
                errors.append("sbom_schema")
            entries = manifest.get("files", [])
            if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
                errors.append("manifest_files_invalid")
                entries = []
            by_name = {str(entry.get("path")): entry for entry in entries}
            if len(by_name) != len(entries):
                errors.append("manifest_duplicate_paths")
            payload_names = set(names) - METADATA_FILES
            if payload_names != set(by_name):
                errors.append("archive_manifest_coverage")
            for name, entry in by_name.items():
                if name not in names:
                    errors.append("missing:" + name)
                    continue
                data = archive.read(name)
                if int(entry.get("size", -1)) != len(data):
                    errors.append("size:" + name)
                if str(entry.get("sha256", "")) != _digest(data):
                    errors.append("sha256:" + name)
            sbom_files = sbom.get("files", [])
            sbom_by_name = {str(item.get("fileName")): item for item in sbom_files if isinstance(item, dict)}
            if set(sbom_by_name) != set(by_name):
                errors.append("sbom_manifest_coverage")
            for name, entry in by_name.items():
                checksums = sbom_by_name.get(name, {}).get("checksums", [])
                values = {str(item.get("checksumValue")) for item in checksums if item.get("algorithm") == "SHA256"}
                if str(entry.get("sha256")) not in values:
                    errors.append("sbom_sha256:" + name)
            report.update({"file_count": len(by_name), "archive_file_count": len(payload_names), "manifest": manifest, "sbom": sbom, "errors": sorted(set(errors))})
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError, KeyError) as exc:
        report["errors"] = ["parse_error:" + type(exc).__name__]
        return report
    report["status"] = "passed" if not report["errors"] else "failed"
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify NOESIS portable artifact manifest and SPDX SBOM")
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = verify(args.artifact)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
