import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from noesis_harness.context_engine import ContextItem
from noesis_harness.memory_ab import ControlledMemoryEvaluator, MemoryABCase
from noesis_harness.trajectory_eval import TrajectoryCheckpoint, TrajectoryEvaluator


def memory_case(index: int) -> MemoryABCase:
    source = f"verified-{index}"
    return MemoryABCase(
        case_id=f"case-{index}",
        query="rollback",
        relevant_source_ids=(source,),
        budget_tokens=12,
        legacy_items=(
            ContextItem("noise", "n" * 32, priority=0.1, source_ids=(f"noise-{index}",)),
            ContextItem("target", "verified rollback state", priority=0.2, source_ids=(source,)),
        ),
        nextgen_items=(
            ContextItem("target", "verified rollback state", priority=10.0, source_ids=(source,), required=True),
            ContextItem("noise", "n" * 32, priority=0.1, source_ids=(f"noise-{index}",)),
        ),
    )


def rollout(index: int, variant: int):
    # Three fixed trajectory shapes model early success, recovery, and late gain.
    shapes = (
        ((0, 0.0), (1, 0.8), (3, 0.8)),
        ((0, 0.0), (1, 0.6), (2, 0.3), (3, 0.7)),
        ((0, 0.0), (2, 0.4), (3, 0.9)),
    )
    checkpoints = tuple(TrajectoryCheckpoint(step, score) for step, score in shapes[variant % len(shapes)])
    return TrajectoryEvaluator(horizon=3).evaluate(checkpoints)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n', type=int, default=100)
    n = max(3, parser.parse_args().n)
    memory = ControlledMemoryEvaluator()
    t0 = time.perf_counter()
    memory_results = [memory.evaluate_case(memory_case(i)) for i in range(n)]
    memory_ms = (time.perf_counter() - t0) * 1000
    rollouts = [[rollout(i, variant) for variant in range(3)] for i in range(n)]
    avg_outcomes = [statistics.mean(m.final_score for m in rows) for rows in rollouts]
    best_outcomes = [max(m.final_score for m in rows) for rows in rollouts]
    avg_c1 = statistics.mean(statistics.mean(m.c1_solution_framing for m in rows) for rows in rollouts)
    avg_c2 = statistics.mean(statistics.mean(m.c2_execution for m in rows) for rows in rollouts)
    avg_c3 = statistics.mean(statistics.mean(m.c3_feedback_control for m in rows) for rows in rollouts)
    print('benchmark,n,metric,value')
    print(f'memory_ab,{n},legacy_recall,{statistics.mean(r.legacy_recall for r in memory_results):.6f}')
    print(f'memory_ab,{n},nextgen_recall,{statistics.mean(r.nextgen_recall for r in memory_results):.6f}')
    print(f'memory_ab,{n},transfer_gain,{statistics.mean(r.transfer_gain for r in memory_results):.6f}')
    print(f'memory_ab,{n},hard_cap_rate,{statistics.mean(1.0 if r.hard_cap_respected else 0.0 for r in memory_results):.6f}')
    print(f'memory_ab,{n},assembly_ms,{memory_ms:.3f}')
    print(f'trajectory,{n},avg_at_3,{statistics.mean(avg_outcomes):.6f}')
    print(f'trajectory,{n},best_at_3,{statistics.mean(best_outcomes):.6f}')
    print(f'trajectory,{n},c1_solution_framing,{avg_c1:.6f}')
    print(f'trajectory,{n},c2_execution,{avg_c2:.6f}')
    print(f'trajectory,{n},c3_feedback_control,{avg_c3:.6f}')


if __name__ == '__main__':
    main()
