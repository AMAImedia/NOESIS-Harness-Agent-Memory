"""benchmarks/bench_redact.py

Stdlib-only benchmark for noesis_harness.redact over N synthetic lines.

Provenance:
  - LoopX   deterministic redaction gate before persistence.
  - Hermes  telemetry redaction pass.

The redact module is imported LAZILY inside main() so importing this
benchmark never pulls the harness package at import time.

Design guarantees (see AGENTS.md):
  - Stdlib only: argparse, json, os, random, re, sys, tempfile, time.
  - redact is imported lazily; no hard dependency on noesis_harness at import.
  - Synthetic input is written only to the system TEMP directory and removed
    before returning. Nothing is written into the repository.
  - Deterministic, idempotent, no LLM, no network, no credentials.

Python 3.9+ syntax only: no `X | None`, no `match`.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import tempfile
import time

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def make_lines(n):
    """Build N synthetic lines; every third line embeds a real-looking email."""
    words = [
        "meeting", "at", "noon", "the", "key", "is", "ready", "report",
        "on", "file", "user", "login", "ok", "token", "value",
    ]
    names = ["alice", "bob", "carol", "dave", "erin"]
    domains = ["example.com", "test.org", "mail.net", "corp.io"]
    rnd = random.Random(1234)
    lines = []
    for i in range(n):
        if i % 3 == 0:
            email = "%s%d@%s" % (rnd.choice(names), i, rnd.choice(domains))
            lines.append(
                "user %s contacted %s about the report"
                % (rnd.choice(words), email)
            )
        else:
            lines.append(" ".join(rnd.choice(words) for _ in range(6)))
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Benchmark noesis_harness.redact over synthetic lines"
    )
    parser.add_argument("--lines", type=int, default=2000)
    args = parser.parse_args(argv)

    from noesis_harness import redact

    lines = make_lines(args.lines)

    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix="bench_redact_", suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))

        start = time.perf_counter()
        redacted = [redact.redact(line) for line in lines]
        seconds = time.perf_counter() - start

        survived = sum(1 for line in redacted if _EMAIL.search(line))
        passed = survived == 0
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    result = {"lines": args.lines, "seconds": round(seconds, 6), "passed": passed}
    print(json.dumps(result))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
