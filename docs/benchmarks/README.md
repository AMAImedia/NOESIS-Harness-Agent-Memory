# NOESIS-Harness-Agent-Memory Benchmarks

## Overview

This directory contains benchmarks for the NOESIS-Harness-Agent-Memory framework.
All benchmarks run on a standard laptop (i7-12700H, 64GB RAM, RTX 3060 6GB VRAM).

## Running Benchmarks

```bash
# Quick benchmark (N=1000)
python benchmarks/memory_bench.py --n 1000

# Full suite
python benchmarks/run_bench.py --all

# Specific sizes
python benchmarks/memory_bench.py --n 100
python benchmarks/memory_bench.py --n 1000
python benchmarks/memory_bench.py --n 5000
python benchmarks/memory_bench.py --n 10000
```

## Expected Results (Reference: i7-12700H, 64GB DDR5, RTX 3060 6GB)

### EventStore
| N | Append ops/sec | Project ops/sec |
|---|----------------|-----------------|
| 100 | ~4,500 | ~320,000 |
| 1,000 | ~5,500 | ~445,000 |
| 5,000 | ~3,900 | ~496,000 |
| 10,000 | ~4,800 | ~306,000 |

### Memory (4-tier)
| N | Save ops/sec | Recall ops/sec | DB Size |
|---|--------------|----------------|---------|
| 100 | ~430 | ~200 | ~0.05 MB |
| 1,000 | ~430 | ~130 | ~0.3 MB |
| 5,000 | ~390 | ~50 | ~1.3 MB |
| 10,000 | ~270 | ~18 | ~2.4 MB |

### Memory Breakdown (N=1000)
- Observations: ~3
- Summaries: ~1
- Semantic: ~4
- Procedural: ~1

## Running in CI

Benchmarks run automatically on push to `main` branch via GitHub Actions.

```yaml
benchmark:
  runs-on: ubuntu-latest
  needs: test
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: "3.11" }
    - run: python benchmarks/run_bench.py --all
```

## Interpreting Results

- **Append ops/sec**: Higher is better. Measures how fast events can be written.
- **Project ops/sec**: Higher is better. Measures replay speed.
- **Save ops/sec**: Memory save throughput (includes FTS5 indexing).
- **Recall ops/sec**: Hybrid search (FTS5 + substring fallback) speed.
- **DB size**: Should grow roughly linearly with N.

## Profiling

To profile a specific operation:

```python
import cProfile, pstats
from benchmarks.memory_bench import bench_memory

profiler = cProfile.Profile()
profiler.enable()
bench_memory(1000, "tmpdir")
profiler.disable()
stats = pstats.Stats(profiler).sort_stats('cumulative')
stats.print_stats(20)
```