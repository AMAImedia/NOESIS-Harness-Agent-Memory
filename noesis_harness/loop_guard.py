"""noesis_harness/loop_guard.py

Detect exact and near-repeat agent actions so a swarm cannot spin.

Pattern adapted from agent-teams loop guard / Hermes turn guards.
Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from collections.abc import Mapping


class LoopGuard:
    def __init__(self, window=8, max_repeats=2):
        if not isinstance(window, int) or isinstance(window, bool) or window < 1:
            raise ValueError("loop_guard_window_invalid")
        if not isinstance(max_repeats, int) or isinstance(max_repeats, bool) or max_repeats < 1 or max_repeats > window:
            raise ValueError("loop_guard_repeats_invalid")
        self.window = window
        self.max_repeats = max_repeats
        self._seen = deque(maxlen=window)

    @staticmethod
    def fingerprint(action):
        if isinstance(action, Mapping):
            payload = json.dumps(dict(action), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        else:
            payload = str(action)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def check(self, action):
        fp = self.fingerprint(action)
        count = sum(1 for x in self._seen if x == fp)
        blocked = count >= self.max_repeats
        self._seen.append(fp)
        return {"ok": not blocked, "repeats": count + 1, "fingerprint": fp}

    def reset(self):
        self._seen.clear()
