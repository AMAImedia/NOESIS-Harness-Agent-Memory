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