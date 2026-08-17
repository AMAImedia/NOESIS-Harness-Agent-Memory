#!/usr/bin/env bash
# bench_all.sh - Run full benchmark suite

set -euo pipefail

echo "Running full benchmark suite..."

echo "=== EventStore benchmarks ==="
python benchmarks/memory_bench.py --n 100
python benchmarks/memory_bench.py --n 1000
python benchmarks/memory_bench.py --n 5000

echo "=== Memory benchmarks ==="
python benchmarks/memory_bench.py --n 1000

echo "=== Running full benchmark suite ==="
python benchmarks/run_bench.py --all

echo "Benchmarks complete!"