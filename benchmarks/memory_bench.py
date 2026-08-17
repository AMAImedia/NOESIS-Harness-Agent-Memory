"""benchmarks/memory_bench.py

NOESIS Memory benchmark: insert, project, search, decay, offload.

Run: python benchmarks/memory_bench.py [--n N]
"""

import argparse
import os
import sys
import tempfile
import time
from typing import Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import Memory, EventStore


def bench_event_store(n: int, state_dir: str) -> Dict[str, float]:
    """Benchmark EventStore append + project."""
    es = EventStore(os.path.join(state_dir, "bench_events.jsonl"))

    # Register reducer
    es.register_reducer("bench", lambda s, p: (s or 0) + 1)

    # Append benchmark
    start = time.perf_counter()
    for i in range(n):
        es.append("bench", {"i": i, "data": "x" * 100})
    append_time = time.perf_counter() - start

    # Project benchmark
    start = time.perf_counter()
    final = es.project(0)
    project_time = time.perf_counter() - start

    # Count
    count = es.count()

    return {
        "events": count,
        "append_sec": append_time,
        "append_ops_sec": n / append_time if append_time > 0 else 0,
        "project_sec": project_time,
        "project_ops_sec": count / project_time if project_time > 0 else 0,
    }


def bench_memory(n: int, state_dir: str) -> Dict[str, float]:
    """Benchmark Memory save + recall + decay + offload."""
    db_path = os.path.join(state_dir, "bench_mem.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    mem = Memory(db_path)

    # Generate test facts
    facts = [f"fact_{i}: client needs service_{i % 10} in language_{i % 5}" for i in range(n)]

    # Save benchmark
    start = time.perf_counter()
    for fact in facts:
        mem.save(fact, kind="semantic", confidence=0.8)
    save_time = time.perf_counter() - start

    # Recall benchmark (10 queries)
    queries = [f"service_{i}" for i in range(10)]
    start = time.perf_counter()
    for q in queries:
        mem.recall(q, limit=5)
    recall_time = time.perf_counter() - start

    # Decay benchmark (10 periods)
    start = time.perf_counter()
    for _ in range(10):
        mem.decay(periods=1)
    decay_time = time.perf_counter() - start

    # Offload benchmark (100 lines each, 10 times)
    log_text = "\n".join([f"Line {i}: event data" for i in range(100)])
    ref_dir = os.path.join(state_dir, "refs")
    os.makedirs(ref_dir, exist_ok=True)
    start = time.perf_counter()
    for i in range(10):
        mem.offload(f"session-{i}", log_text, ref_dir)
    offload_time = time.perf_counter() - start

    stats = mem.stats()

    return {
        "memories": stats["memories"],
        "save_sec": save_time,
        "save_ops_sec": n / save_time if save_time > 0 else 0,
        "recall_sec": recall_time,
        "recall_ops_sec": 10 / recall_time if recall_time > 0 else 0,
        "decay_sec": decay_time,
        "offload_sec": offload_time,
        "db_size_mb": os.path.getsize(os.path.join(state_dir, "bench_mem.db")) / (1024 * 1024),
    }


def run_benchmarks(n: int) -> Dict:
    """Run all benchmarks and return results."""
    state_dir = tempfile.mkdtemp(prefix="noesis_bench_")

    print(f"Running benchmarks with N={n}...")
    print(f"State dir: {state_dir}")

    results = {}
    results["event_store"] = bench_event_store(n, state_dir)
    results["memory"] = bench_memory(n, state_dir)

    return results


def print_results(results: Dict):
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)

    es = results["event_store"]
    print(f"\nEventStore ({es['events']} events):")
    print(f"  Append:  {es['append_sec']:.4f}s  ({es['append_ops_sec']:,.0f} ops/sec)")
    print(f"  Project: {es['project_sec']:.4f}s  ({es['project_ops_sec']:,.0f} ops/sec)")

    mem = results["memory"]
    print(f"\nMemory ({mem['memories']} facts):")
    print(f"  Save:    {mem['save_sec']:.4f}s  ({mem['save_ops_sec']:,.0f} ops/sec)")
    print(f"  Recall:  {mem['recall_sec']:.4f}s  ({mem['recall_ops_sec']:,.0f} ops/sec)")
    print(f"  Decay:   {mem['decay_sec']:.4f}s  (10 periods x {mem['memories']} facts)")
    print(f"  Offload: {mem['offload_sec']:.4f}s  (10 x 100 lines)")
    print(f"  DB size: {mem['db_size_mb']:.2f} MB")


def main():
    parser = argparse.ArgumentParser(description="NOESIS Memory Benchmark")
    parser.add_argument("--n", type=int, default=1000, help="Number of events/facts (default: 1000)")
    args = parser.parse_args()

    results = run_benchmarks(args.n)
    print_results(results)


if __name__ == "__main__":
    main()