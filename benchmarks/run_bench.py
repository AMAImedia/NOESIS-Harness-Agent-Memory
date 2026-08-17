#!/usr/bin/env python3
"""benchmarks/run_bench.py

Wrapper script to run memory benchmarks with multiple N values.

Usage:
  python run_bench.py           # default: 100, 1000, 5000
  python run_bench.py --n 10000 # single run
  python run_bench.py --all     # all predefined sizes
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memory_bench import run_benchmarks, print_results


def main():
    parser = argparse.ArgumentParser(description="NOESIS Memory Benchmark Runner")
    parser.add_argument("--n", type=int, help="Single run with N events")
    parser.add_argument("--all", action="store_true", help="Run all predefined sizes")
    args = parser.parse_args()

    if args.all:
        sizes = [100, 1000, 5000, 10000]
    elif args.n:
        sizes = [args.n]
    else:
        sizes = [100, 1000, 5000]

    print(f"NOESIS Memory Benchmark Suite")
    print(f"Testing sizes: {sizes}")

    all_results = {}
    for n in sizes:
        try:
            results = run_benchmarks(n)
            all_results[n] = results
            print_results(results)
        except Exception as e:
            print(f"Error at N={n}: {e}")

    # Summary table
    print("\n" + "=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    print(f"{'N':>8} | {'Append ops/s':>14} | {'Project ops/s':>14} | {'Save ops/s':>12} | {'Recall ops/s':>12} | {'DB Size MB':>10}")
    print("-" * 80)
    for n in sizes:
        if n not in all_results:
            continue
        es = all_results[n]["event_store"]
        mem = all_results[n]["memory"]
        print(f"{n:>8} | {es['append_ops_sec']:>14,.0f} | {es['project_ops_sec']:>14,.0f} | {mem['save_ops_sec']:>12,.0f} | {mem['recall_ops_sec']:>12,.0f} | {mem['db_size_mb']:>10.2f}")

    print("=" * 80)


if __name__ == "__main__":
    main()