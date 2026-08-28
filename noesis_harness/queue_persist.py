"""noesis_harness/queue_persist.py — file-backed queue.

Patterns: LoopX durable queue.
Stdlib only.
"""
from __future__ import annotations
import json, os, threading

class FileQueue:
    def __init__(self, path: str):
        self.path = path; self._lock = threading.Lock()
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        if not os.path.isfile(path):
            open(path, "w").write("[]")
    def push(self, item) -> None:
        with self._lock:
            data = json.loads(open(self.path, encoding="utf-8").read())
            data.append(item)
            open(self.path, "w", encoding="utf-8").write(json.dumps(data))
    def pop(self):
        with self._lock:
            data = json.loads(open(self.path, encoding="utf-8").read())
            if not data: return None
            item = data.pop(0)
            open(self.path, "w", encoding="utf-8").write(json.dumps(data))
            return item
    def peek(self):
        data = json.loads(open(self.path, encoding="utf-8").read())
        return data[0] if data else None
    def __len__(self):
        return len(json.loads(open(self.path, encoding="utf-8").read()))
