"""noesis_harness/config_store.py — append-only config store.

Patterns: LoopX config projection.
Stdlib only.
"""
from __future__ import annotations
import json, os, threading

class ConfigStore:
    def __init__(self, path: str):
        self.path = path; self._lock = threading.Lock()
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    def set(self, key: str, value) -> None:
        cfg = self.get_all(); cfg[key] = value
        with self._lock:
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, sort_keys=True, ensure_ascii=False)
    def get(self, key: str, default=None):
        return self.get_all().get(key, default)
    def get_all(self):
        if not os.path.isfile(self.path): return {}
        try: return json.loads(open(self.path, encoding="utf-8").read())
        except (ValueError, OSError): return {}
