"""noesis_harness/loop_guard.py

Detect exact and near-repeat agent actions so a swarm cannot spin.

Pattern adapted from agent-teams loop guard / Hermes turn guards.
Stdlib only.
"""

from __future__ import annotations

import hashlib
from collections import deque


class LoopGuard:
    def __init__(self, window=8, max_repeats=2):
        self.window = window
        self.max_repeats = max_repeats
        self._seen = deque(maxlen=window)

    @staticmethod
    def fingerprint(action):
        return hashlib.sha256(str(action).encode("utf-8")).hexdigest()

    def check(self, action):
        fp = self.fingerprint(action)
        count = sum(1 for x in self._seen if x == fp)
        blocked = count >= self.max_repeats
        self._seen.append(fp)
        return {"ok": not blocked, "repeats": count + 1, "fingerprint": fp}

    def reset(self):
        self._seen.clear()
