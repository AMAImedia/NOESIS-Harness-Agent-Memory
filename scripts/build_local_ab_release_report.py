#!/usr/bin/env python3
"""Build a deterministic local A/B release report with provenance and audit chain."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from scripts.ingest_runner_result import canonical, signature
from scripts.run_local_signed_ab_fixture import FIXTURE_KEY, run as run_fixture

SCHEMA = "noesis.local-ab-release.v1"


def audit_event(sequence: int, event_type: str, payload: Mapping[str, Any], previous: str) -> tuple[dict, str]:
    unsigned = {"seq": sequence, "type": event_type, "payload": dict(payload), "prev_hash": previous}
    digest = hashlib.sha256(canonical(unsigned)).hexdigest()
    return {**unsigned, "event_hash": digest}, digest


def verify_report(report: Mapping[str, Any], key: str) -> bool:
    events = report.get("audit", [])
    previous = "0" * 64
    for expected, event in enumerate(events, start=1):
        unsigned = {name: value for name, value in event.items() if name != "event_hash"}
        if event.get("seq") != expected or event.get("prev_hash") != previous:
            return False
        digest = hashlib.sha256(canonical(unsigned)).hexdigest()
        if event.get("event_hash") != digest:
            return False
        previous = digest
    signed = {name: value for name, value in report.items() if name != "signature"}
    return report.get("signature") == signature(signed, key)


def build(output: str, key: str = FIXTURE_KEY) -> dict:
    fixture_path = Path(output).with_suffix(".fixture.json")
    fixture = run_fixture(str(fixture_path))
    evidence_digests = [item.get("source_result_sha256", "") for item in fixture["evidence"]]
    provenance = {
        "fixture_schema": fixture["schema_version"],
        "task_manifest_sha256": fixture["task_manifest_sha256"],
        "evidence_source_result_sha256": evidence_digests,
        "external_processes_started": fixture["external_processes_started"],
    }
    events = []
    previous = "0" * 64
    for event_type, payload in (
        ("fixture_created", {"task_manifest_sha256": fixture["task_manifest_sha256"]}),
        ("evidence_ingested", {"count": len(fixture["evidence"]), "digests": evidence_digests}),
        ("evaluation_completed", {"comparable": fixture["evaluation"]["comparable"], "systems": fixture["evaluation"]["systems"]}),
    ):
        event, previous = audit_event(len(events) + 1, event_type, payload, previous)
        events.append(event)
    unsigned = {
        "schema_version": SCHEMA,
        "simulation_only": True,
        "provenance": provenance,
        "audit": events,
        "evaluation": fixture["evaluation"],
        "report_sha256_basis": hashlib.sha256(canonical({"provenance": provenance, "audit": events, "evaluation": fixture["evaluation"]})).hexdigest(),
    }
    report = {**unsigned, "signature": signature(unsigned, key)}
    if not verify_report(report, key):
        raise RuntimeError("self-verification failed")
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build local NOESIS A/B release report")
    parser.add_argument("--output", required=True)
    parser.add_argument("--key", default=FIXTURE_KEY)
    args = parser.parse_args(argv)
    report = build(args.output, args.key)
    print(json.dumps({"output": args.output, "schema": report["schema_version"], "comparable": report["evaluation"]["comparable"], "audit_events": len(report["audit"]), "external_processes_started": report["provenance"]["external_processes_started"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
