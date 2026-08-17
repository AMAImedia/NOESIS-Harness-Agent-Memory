"""End-to-end local runtime: memory + queue + loop guard + judge. Stdlib only."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import (
    Memory, DurableQueue, LoopGuard, HybridJudge, PrivacyFilter,
)


def main():
    root = tempfile.mkdtemp(prefix="noesis_runtime_")
    mem = Memory(os.path.join(root, "mem.db"), privacy=PrivacyFilter())
    q = DurableQueue(os.path.join(root, "q.db"))
    guard = LoopGuard()
    judge = HybridJudge()
    mem.save("when inbound spanish then reply in spanish", kind="procedural")
    tid = q.enqueue({"text": "need Spanish dub, mail me@x.com"})
    job = q.lease("worker-1")[0]
    text = job["payload"]["text"]
    mem.observe("s1", "inbound", text)
    chk = guard.check(text)
    verdict = judge.judge([text])
    q.ack(tid)
    print("lease", job["id"][:8], "guard", chk["ok"], "judge", verdict["pass"])
    print("memory", mem.stats())
    print("queue", q.stats())


if __name__ == "__main__":
    main()
