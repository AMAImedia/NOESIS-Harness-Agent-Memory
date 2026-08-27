"""Micro-benchmark for noesis_harness.digest_utils.

Patterns borrowed from:
- LoopX: deterministic, order-independent event fingerprinting used for
  idempotent append-only state projection. This benchmark asserts that the
  canonicalization + hashing path is both fast and stable, which is what makes
  the LoopX-style fingerprints safe to use as content addresses.

This module is stdlib-only and writes nothing outside the system TEMP
directory. digest_utils is imported lazily so the benchmark can be collected
by the test runner even if the package import path is not yet set up.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _make_payloads(ops):
    """Build ``ops`` synthetic payloads with deterministic, varied content."""
    payloads = []
    for i in range(ops):
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


def bench(ops):
    """Time canonical_json + sha256_hex over ``ops`` synthetic payloads.

    Imports digest_utils lazily. Returns a result dict with ops, seconds, and
    passed (determinism check). All intermediate state lives in TEMP.
    """
    import noesis_harness.digest_utils as du

    scratch = tempfile.mkdtemp(prefix="noesis_bench_digest_")
    payloads = _make_payloads(ops)

    start = time.perf_counter()
    digests = []
    for payload in payloads:
        digests.append(du.sha256_hex(du.canonical_json(payload)))
    seconds = time.perf_counter() - start

    with open(os.path.join(scratch, "digests.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(digests))

    passed = True
    for payload, digest in zip(payloads, digests):
        again = du.sha256_hex(du.canonical_json(payload))
        if again != digest:
            passed = False
            break

    return {"ops": ops, "seconds": seconds, "passed": passed}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Micro-benchmark digest_utils.")
    parser.add_argument("--ops", type=int, default=1000, help="number of payloads")
    args = parser.parse_args(argv)

    result = bench(args.ops)
    print(json.dumps(result))

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
