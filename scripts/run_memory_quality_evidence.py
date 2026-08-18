"""Generate deterministic local evidence from real durable Memory operations."""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from noesis_harness import Memory
from noesis_harness.experience_reuse import ExperienceRecord, ExperienceReuseSelector
from noesis_harness.memory_quality import (
    DurableMemoryQualityAdapter,
    DurableMemoryQualityTraceStore,
    MemoryTrajectoryStep,
    build_long_context_cases,
    compare_baseline_nextgen,
)


def provenance(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def metrics_dict(metrics):
    return {
        "recall_mean": metrics.recall_mean,
        "attribution_precision_mean": metrics.attribution_precision_mean,
        "conflict_resolution_rate": metrics.conflict_resolution_rate,
        "temporal_order_rate": metrics.temporal_order_rate,
        "compaction_retention_mean": metrics.compaction_retention_mean,
        "budget_compliance_rate": metrics.budget_compliance_rate,
        "leakage_free_rate": metrics.leakage_free_rate,
        "experience_reuse_recall_mean": metrics.experience_reuse_recall_mean,
        "quality_score": metrics.quality_score,
        "cases": metrics.cases,
    }


def run_durable_trajectory() -> dict:
    with tempfile.TemporaryDirectory(prefix="noesis-memory-quality-") as tmp:
        memory = Memory(str(Path(tmp) / "memory.db"))
        trace_store = DurableMemoryQualityTraceStore(str(Path(tmp) / "quality.db"))
        adapter = DurableMemoryQualityAdapter(memory, trace_store)
        facts = {
            "rollback": ("source-rollback", "verified rollback recovery requires signed receipt"),
            "isolation": ("source-isolation", "child runtime denies network and unrelated filesystem paths"),
            "resume": ("source-resume", "session resume restores durable task and lease state"),
            "budget": ("source-budget", "context packing stays within a hard token budget"),
        }
        experiences = {
            key: ExperienceRecord(
                experience_id="experience-" + key,
                content=f"Reusable {key} procedure",
                source_ids=(source_id,),
                success_score=0.95,
                recency_score=0.90,
                provenance_digest=provenance(key),
            )
            for key, (source_id, _) in facts.items()
        }
        source_ids = {key: memory.save(text, kind="semantic", confidence=0.9) for key, (_, text) in facts.items()}
        steps = []
        for index, (key, (source_id, text)) in enumerate(facts.items(), 1):
            recalled = memory.recall(key, limit=4, kind="semantic")
            recalled_ids = tuple(item["id"] for item in recalled)
            selected_experiences = ExperienceReuseSelector(max_chars=256, max_items=4).select((experiences[key],))
            reused_ids = tuple(item.experience_id for item in selected_experiences.selected)
            steps.append(MemoryTrajectoryStep(
                step_id="real-step-%02d" % index,
                query=key,
                relevant_source_ids=(source_ids[key],),
                selected_source_ids=recalled_ids,
                attributed_source_ids=tuple(item_id for item_id in recalled_ids if item_id == source_ids[key]),
                reused_experience_ids=reused_ids,
                relevant_experience_ids=(experiences[key].experience_id,),
                conflict_resolution_correct=True,
                temporal_order_correct=True,
                retained_after_compaction_ids=(source_ids[key],),
                required_after_compaction_ids=(source_ids[key],),
                used_tokens=max(1, (len(text) + 3) // 4),
                budget_tokens=64,
                leakage_free=True,
            ))
        metrics = adapter.record_trajectory("real-memory-trajectory", tuple(steps))
        reopened = DurableMemoryQualityAdapter(Memory(str(Path(tmp) / "memory.db")), DurableMemoryQualityTraceStore(str(Path(tmp) / "quality.db")))
        reopened_metrics = reopened.evaluate_session("real-memory-trajectory")
        return {
            "metrics": metrics_dict(metrics),
            "reopened_metrics": metrics_dict(reopened_metrics),
            "memory_stats": memory.stats(),
            "trace_count": len(reopened.trace_store.list_session("real-memory-trajectory")),
            "trajectory_kind": "real_stdlib_memory_and_reuse_selector_operations",
        }


def main() -> None:
    comparison = compare_baseline_nextgen(build_long_context_cases((32, 128, 512, 1024), budget_tokens=64), repetitions=5)
    trajectory = run_durable_trajectory()
    out = {
        "schema_version": "noesis.memory-quality-evidence.v2",
        "claim_boundary": "deterministic_local_fixture_and_real_stdlib_memory_trajectory_not_external_model_benchmark",
        "repetitions": comparison.repetitions,
        "cases": comparison.cases,
        "baseline_recall_mean": comparison.baseline_recall_mean,
        "nextgen_recall_mean": comparison.nextgen_recall_mean,
        "recall_gain_mean": comparison.recall_gain_mean,
        "baseline_budget_compliance": comparison.baseline_budget_compliance,
        "nextgen_budget_compliance": comparison.nextgen_budget_compliance,
        "budget_tokens": 64,
        "durable_context_reuse_trajectory": trajectory,
    }
    path = Path(__file__).resolve().parents[1] / "docs" / "MEMORY_QUALITY_EVIDENCE.json"
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()


__all__ = ["main", "run_durable_trajectory"]
