#!/usr/bin/env python3
"""Run a deterministic local signed-evidence A/B fixture lane.

This lane validates the ingestion/evaluation plumbing only. It never starts
Hermes, OpenCode, a model provider, or a generated command.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from scripts.evaluate_signed_ab import evaluate
from scripts.external_runner_contract import make_spec
from scripts.ingest_runner_result import ingest

FIXTURE_KEY = "local-fixture-evidence-key-2026"


def fixture_result(system: str, revision: str, task_digest: str, latency_ms: float) -> tuple[dict, dict]:
    spec = make_spec(system, revision, [system, "fixture", "--no-exec"], task_digest, model_provider="fixture-model-v1")
    result = {
        **spec,
        "execution": "fixture_only",
        "status": "passed",
        "metrics": {
            "task_success": {"status": "observed", "value": 1.0},
            "test_pass_rate": {"status": "observed", "value": 1.0},
            "latency_ms": {"status": "observed", "value": latency_ms},
            "patch_correctness": {"status": "not_run", "reason": "fixture lane does not execute coding tasks"},
            "unauthorized_egress": {"status": "observed", "value": 0.0},
            "credential_exposure": {"status": "observed", "value": 0.0},
        },
    }
    return spec, result


def run(output: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="noesis-local-ab-") as directory:
        task_manifest = Path(directory) / "task-manifest.json"
        task_manifest.write_text(json.dumps({"fixture": "signed-local-ab-v1", "seed": 17}, sort_keys=True) + "\n", encoding="utf-8")
        import hashlib
        digest = hashlib.sha256(task_manifest.read_bytes()).hexdigest()
        specs_results = [fixture_result("hermes", "fixture-hermes-r1", digest, 10.0), fixture_result("opencode", "fixture-opencode-r1", digest, 12.0)]
        evidence = [ingest(spec, result, FIXTURE_KEY) for spec, result in specs_results]
        evaluation = evaluate(evidence, FIXTURE_KEY)
        report = {
            "schema_version": "noesis.local-signed-ab-fixture.v1",
            "simulation_only": True,
            "external_processes_started": False,
            "task_manifest_sha256": digest,
            "evidence": evidence,
            "evaluation": evaluation,
        }
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic local signed A/B fixture lane")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report = run(args.output)
    print(json.dumps({"output": args.output, "comparable": report["evaluation"]["comparable"], "external_processes_started": report["external_processes_started"]}, ensure_ascii=False))
    return 0 if report["evaluation"]["comparable"] and not report["external_processes_started"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
