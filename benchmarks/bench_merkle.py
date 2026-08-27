"""Micro-benchmark for noesis_harness.merkle_chain.

Patterns borrowed from:
- deepseek-harness: an append-only event log where each entry carries the
  digest of the previous entry, so the log is tamper-evident. This benchmark
  exercises that exact append-only path and confirms verify() stays True,
  which is the property deepseek-harness relies on for a trustworthy replay log.
- LoopX: a deterministic, idempotent append path where the only mutating op is
  append() and the canonical digest is a pure function of (prev_digest,
  payload). This benchmark times the append loop and the full-chain verify so
  the LoopX-style stable replay projection can be costed.

This module is stdlib-only and writes nothing outside the system TEMP
directory. merkle_chain is imported lazily so the benchmark can be collected by
the test runner even if the package import path is not yet set up.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _make_payloads(n):
    """Build ``n`` synthetic payloads with deterministic, varied content."""
    payloads = []
    for i in range(n):
        payloads.append(
            {
                "idx": i,
                "kind": "event",
                "agent": "agent-%d" % (i % 7),
                "data": {
                    "value": i * 2,
                    "label": "item-%d" % i,
                    "flag": (i % 3 == 0),
                },
                "tags": ["t%d" % (i % 5), "core"],
            }
        )
    return payloads


def bench(entries):
    """Append ``entries`` entries to a HashChain and time append + verify.

    Imports merkle_chain lazily. Returns a result dict with entry count, append
    seconds, verify seconds, and passed (verify() True). All intermediate state
    lives in TEMP.
    """
    import noesis_harness.merkle_chain as mc

    scratch = tempfile.mkdtemp(prefix="noesis_bench_merkle_")
    payloads = _make_payloads(entries)

    chain = mc.HashChain()

    append_start = time.perf_counter()
    for payload in payloads:
        chain.append(payload)
    append_sec = time.perf_counter() - append_start

    verify_start = time.perf_counter()
    passed = chain.verify()
    verify_sec = time.perf_counter() - verify_start

    with open(os.path.join(scratch, "chain_len.txt"), "w", encoding="utf-8") as fh:
        fh.write(str(len(chain)))

    return {
        "entries": entries,
        "append_sec": append_sec,
        "verify_sec": verify_sec,
        "passed": passed,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Micro-benchmark merkle_chain.")
    parser.add_argument("--entries", type=int, default=1000, help="number of entries")
    args = parser.parse_args(argv)

    result = bench(args.entries)
    print(json.dumps(result))

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
