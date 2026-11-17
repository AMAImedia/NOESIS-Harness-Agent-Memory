"""Provider-neutral CLI for deterministic signed report bundles."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from noesis_harness.report_bundle import build_report_bundle, verify_report_bundle


def _read_json(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("domain_json_must_be_object")
    return value


def _key(env_name: str) -> bytes:
    value = os.environ.get(env_name, "")
    if len(value.encode("utf-8")) < 16:
        raise ValueError("signing_key_environment_value_too_short")
    return value.encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or verify deterministic signed NOESIS report bundles")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--local", required=True, dest="local_execution")
    create.add_argument("--native", required=True, dest="native_parity")
    create.add_argument("--external", required=True, dest="external_comparative")
    create.add_argument("--output", required=True)
    create.add_argument("--key-env", default="NOESIS_REPORT_SIGNING_KEY")
    verify = subparsers.add_parser("verify")
    verify.add_argument("--bundle", required=True)
    verify.add_argument("--key-env", default="NOESIS_REPORT_SIGNING_KEY")
    args = parser.parse_args(argv)
    try:
        key = _key(args.key_env)
        if args.command == "create":
            result = build_report_bundle(args.output, local_execution=_read_json(args.local_execution), native_parity=_read_json(args.native_parity), external_comparative=_read_json(args.external_comparative), signing_key=key)
            print(json.dumps(result, sort_keys=True))
            return 0
        result = verify_report_bundle(args.bundle, key)
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("status") == "passed" else 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "reason": type(exc).__name__ + ":" + str(exc)[:160]}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
