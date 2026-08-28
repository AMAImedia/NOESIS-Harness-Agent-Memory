"""noesis_harness/log_buffer.py — in-memory log buffer by level.

Patterns: LoopX logging.
Stdlib only.
"""
from __future__ import annotations
from collections import deque
import threading

class LogBuffer:
    def __init__(self, capacity: int = 100):
        self.capacity = capacity; self._buf = deque(maxlen=capacity); self._lock = threading.Lock()
    def log(self, level: str, msg: str) -> None:
        with self._lock: self._buf.append((level, msg))
    def entries(self, level: str = None):
        with self._lock:
            vals = list(self._buf)
        if level is None: return vals
        return [e for e in vals if e[0] == level]
    def clear(self) -> None:
        with self._lock: self._buf.clear()
    def __len__(self):
        with self._lock: return len(self._buf)
