"""Create or verify a signed release-readiness receipt offline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.signed_readiness_receipt import sign_readiness_receipt, verify_readiness_receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or verify a NOESIS signed readiness receipt")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--gate-artifact", required=True)
    parser.add_argument("--test-count", required=True, type=int)
    parser.add_argument("--python-version", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    gate = json.loads(Path(args.gate_artifact).read_text(encoding="utf-8"))
    receipt = sign_readiness_receipt(snapshot, gate, args.test_count, args.python_version, args.key)
    check = verify_readiness_receipt(receipt, snapshot, gate, args.test_count, args.key)
    if check.get("status") != "passed":
        raise SystemExit(2)
    Path(args.output).write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "receipt_digest": receipt["receipt_digest"], "output": str(Path(args.output).resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
