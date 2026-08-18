"""Validate operator-produced native parity artifacts fail-closed."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from noesis_harness.native_parity import validate_native_artifacts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate native parity artifacts")
    parser.add_argument("--target", choices=("windows", "macos"), required=True)
    parser.add_argument("--evidence-dir", required=True)
    args = parser.parse_args(argv)
    evidence = validate_native_artifacts(args.target, Path(args.evidence_dir))
    print(json.dumps(evidence.to_mapping(), sort_keys=True))
    return 0 if evidence.status == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
