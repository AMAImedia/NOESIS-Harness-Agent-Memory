#!/usr/bin/env python3
import json
from pathlib import Path
from noesis_harness.memory_quality import build_long_context_cases, compare_baseline_nextgen

report = compare_baseline_nextgen(build_long_context_cases((32, 128, 512, 1024), budget_tokens=64), repetitions=5)
out = {
    "schema_version": "noesis.memory-quality-evidence.v1",
    "claim_boundary": "deterministic_local_fixture_not_external_model_benchmark",
    "repetitions": report.repetitions,
    "cases": report.cases,
    "baseline_recall_mean": report.baseline_recall_mean,
    "nextgen_recall_mean": report.nextgen_recall_mean,
    "recall_gain_mean": report.recall_gain_mean,
    "baseline_budget_compliance": report.baseline_budget_compliance,
    "nextgen_budget_compliance": report.nextgen_budget_compliance,
    "budget_tokens": 64,
}
path = Path(__file__).resolve().parents[1] / "docs" / "MEMORY_QUALITY_EVIDENCE.json"
path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(out, sort_keys=True))
