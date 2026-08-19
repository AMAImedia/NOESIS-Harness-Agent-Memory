"""Export a signed report bundle from a bounded operator snapshot JSON."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from noesis_harness.report_bundle import build_report_bundle


def _read(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("snapshot_must_be_object")
    return value


def _domain(snapshot: Mapping[str, Any], name: str, fallback: Mapping[str, Any]) -> dict[str, Any]:
    value = snapshot.get(name)
    if not isinstance(value, Mapping):
        telemetry = snapshot.get("telemetry")
        if isinstance(telemetry, Mapping):
            value = telemetry.get(name)
    return dict(value) if isinstance(value, Mapping) else dict(fallback)


def _key(env_name: str) -> bytes:
    raw = os.environ.get(env_name, "")
    if len(raw.encode("utf-8")) < 16:
        raise ValueError("signing_key_environment_value_too_short")
    return raw.encode("utf-8")


def export_snapshot(snapshot: Mapping[str, Any], output: str, key: bytes) -> Mapping[str, Any]:
    local = _domain(snapshot, "local_execution", {"status": "not_run", "reason": "local_execution_projection_unavailable", "execution_claim": False})
    native = _domain(snapshot, "native_parity", {"status": "not_run", "reason": "native_parity_projection_unavailable", "execution_claim": False})
    external = _domain(snapshot, "external_comparative", {"status": "not_run", "reason": "external_comparative_projection_unavailable", "comparative_claim": False, "external_execution_claim": False})
    for value in (local, native, external):
        value.pop("signing_key", None)
        value.pop("operator_token", None)
    return build_report_bundle(output, local_execution=local, native_parity=native, external_comparative=external, signing_key=key)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export a signed report bundle from a bounded operator snapshot")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--key-env", default="NOESIS_REPORT_SIGNING_KEY")
    args = parser.parse_args(argv)
    try:
        result = export_snapshot(_read(args.snapshot), args.output, _key(args.key_env))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "reason": type(exc).__name__ + ":" + str(exc)[:160]}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
