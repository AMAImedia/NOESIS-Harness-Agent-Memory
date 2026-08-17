#!/usr/bin/env python3
"""Verify that the active interpreter is exactly Python 3.14 for release gates."""
from __future__ import annotations

import argparse
import json
import sys


def verify() -> dict:
    version = "%d.%d.%d" % sys.version_info[:3]
    ok = sys.version_info[:2] == (3, 14)
    return {"ok": ok, "required": "3.14.x", "actual": version, "implementation": sys.implementation.name}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify NOESIS Python 3.14-only release runtime")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = verify()
    print(json.dumps(result, sort_keys=True) if args.json else ("Python 3.14 verification PASS: " + result["actual"] if result["ok"] else "Python 3.14 verification BLOCKED: " + result["actual"]))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
