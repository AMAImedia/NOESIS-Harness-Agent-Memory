# NOESIS Memory Benchmarks

## Overview

Benchmarks for the NOESIS Memory module (`noesis_harness.Memory`):
- **EventStore**: append + deterministic projection
- **Memory**: 4-tier storage (save/recall/decay/offload)

All benchmarks use **stdlib only** (sqlite3, hashlib, json, threading).

---

## Running Benchmarks

### Quick run (default sizes: 100, 1000, 5000)

```bash
cd NOESIS-Harness-Agent-Memory
python benchmarks/run_bench.py
```

### Single size

```bash
python benchmarks/run_bench.py --n 1000
```

### All sizes (100, 1000, 5000, 10000)

```bash
python benchmarks/run_bench.py --all
```

### Direct module run

```bash
python benchmarks/memory_bench.py --n 1000
```

---

## Fixed 20-item Gates

Two one-line deterministic gate benches with fixed fixtures (no wall clock,
no randomness). Each prints exactly one line and uses its exit code for CI.

```bash
python benchmarks/recall20.py    # -> 'recall20 20/20 acc=1.00'   exit 0 if acc>=0.8 else 1
python benchmarks/workload20.py  # -> 'workload20 score=...'      exit 0 if score>0 and MA-07 probe passes
```

### recall20 — public recall bench

Runs the fixed 20-fact / 20-query spec in `recall20.json` through
`noesis_harness.Memory` in a tempdir and reports hit rate over substring
matching of expected facts.

Output: `recall20 <hit>/<n> acc=<x.xx>` — exits `0` when `acc >= 0.8`, else `1`.

### workload20 — Gate 4 work-product bench

Scores a fixed deterministic 20-outcome tuple (`w20-01`..`w20-20`, mix of
correct/delivered/leakage-free/recovered lanes, attempts within [1..4]) through
`noesis_harness.work_product_benchmark.WorkProductBenchmarkEvaluator`, then
folds in one tiny live MA-07 runner pass (3 lanes, injected first-attempt crash
on one lane, `retry_limit=1`) inside a tempdir (~0.15 s; well under any budget).

Output: `workload20 score=<0.xxxx> correctness=<x.xx> leakage_free=<x.xx>
recovery=<x.xx>` — exits `0` when score > 0 and the MA-07 probe passes, `2`
when score <= 0, `1` when only the MA-07 probe fails.

---

## What is Measured

| Component | Metric | Description |
|-----------|--------|-------------|
| **EventStore.append** | ops/sec | Idempotent append with fingerprint dedup |
| **EventStore.project** | ops/sec | Deterministic replay through reducers |
| **Memory.save** | ops/sec | Deduplicated fact insert + FTS5 index update |
| **Memory.recall** | ops/sec | Hybrid FTS5 + substring search + strength ranking |
| **Memory.decay** | sec | Ebbinghaus decay pass over all facts (10 periods) |
| **Memory.offload** | sec | Write log to refs/ + summary pointer (10 x 100 lines) |
| **DB size** | MB | SQLite file size after benchmark |

---

## Expected Results (Reference: i7-12700H, 64 GB DDR5, NVMe)

| N | EventStore append | EventStore project | Memory save | Memory recall | DB size |
|---|-------------------|-------------------|-------------|---------------|---------|
| 100 | ~15,000 ops/s | ~25,000 ops/s | ~12,000 ops/s | ~8,000 ops/s | ~0.1 MB |
| 1,000 | ~12,000 ops/s | ~20,000 ops/s | ~10,000 ops/s | ~6,000 ops/s | ~0.5 MB |
| 5,000 | ~10,000 ops/s | ~15,000 ops/s | ~8,000 ops/s | ~4,000 ops/s | ~2 MB |
| 10,000 | ~8,000 ops/s | ~12,000 ops/s | ~6,000 ops/s | ~3,000 ops/s | ~4 MB |

*Note: Results vary by hardware. FTS5 indexing overhead grows with corpus size.*

---

## Output Files

- `bench_events.jsonl` — EventStore log (JSONL)
- `bench_mem.db` — SQLite database with FTS5
- `refs/` — Offload reference files (markdown)

All created in a temporary directory, cleaned up after run.

---

## Adding Custom Benchmarks

Extend `memory_bench.py` with new benchmark functions:

```python
def bench_custom(n: int, state_dir: str) -> Dict:
    # Your benchmark logic
    return {"metric": value}
```

Add to `run_benchmarks()` and `print_results()`.

---

## CI Integration

The benchmark runs automatically in CI (`.github/workflows/ci.yml`):

```yaml
- name: Run benchmarks
  run: python benchmarks/run_bench.py --all
```

Results printed to CI logs for regression tracking.