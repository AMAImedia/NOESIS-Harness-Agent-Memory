"""noesis_harness/consolidate.py

Periodic memory consolidation: decay + merge near-duplicate facts.

Pattern adapted from TencentDB-Agent-Memory consolidation + agentmemory
strength merge. Stdlib only, no LLM required (optional compressor via Memory).
"""

from __future__ import annotations

import re


_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def _norm(text):
    return _WS.sub(" ", _PUNCT.sub("", (text or "").lower())).strip()


class ConsolidationWorker:
    """Run decay then collapse facts with identical normalized text."""

    def __init__(self, memory, periods=1):
        self.memory = memory
        self.periods = periods

    def run_once(self):
        decayed = self.memory.decay(self.periods)
        merged = 0
        with self.memory._lock, self.memory._conn() as c:
            rows = c.execute(
                "SELECT id, fact, strength, access_count, created_at "
                "FROM memories ORDER BY created_at ASC").fetchall()
            seen = {}
            drop = []
            for r in rows:
                key = _norm(r["fact"])
                if not key:
                    continue
                if key in seen:
                    keep = seen[key]
                    c.execute(
                        "UPDATE memories SET strength=MIN(2.0, strength+?),"
                        " access_count=access_count+? WHERE id=?",
                        (r["strength"], r["access_count"], keep))
                    drop.append(r["id"])
                    merged += 1
                else:
                    seen[key] = r["id"]
            for mid in drop:
                c.execute("DELETE FROM memories WHERE id=?", (mid,))
        return {"decayed": decayed, "merged": merged}
