#!/usr/bin/env python3
"""Run backend command-level conformance and emit honest host evidence."""
from __future__ import annotations

import argparse
import json
import platform
import sys
import tempfile
from pathlib import Path

from noesis_harness.sandbox_backend import inspect_backend
from noesis_harness.sandbox_bwrap import BubblewrapBackend
from noesis_harness.sandbox_macos import MacOSSandboxBackend


def build_report() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="noesis-sandbox-conformance-") as temp:
        workspace = Path(temp)
        backends = (BubblewrapBackend(), MacOSSandboxBackend())
        records = [inspect_backend(backend, workspace=workspace).as_dict() for backend in backends]
    records.append({
        "backend_id": "windows-native",
        "host_platform": "windows",
        "available": False,
        "checks": [],
        "reason": "matching_windows_host_required",
        "status": "not_run",
    })
    return {
        "schema_version": "noesis.sandbox-conformance.v1",
        "runtime": {"python": platform.python_version(), "platform": platform.platform(), "system": platform.system()},
        "records": records,
        "external_boundary": "macOS/Windows execution evidence requires matching native host; Linux does not simulate it",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = build_report()
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
