"""noesis_harness/feature_flag.py — read-only feature flags.

Patterns: LoopX/agentmemory read-only view.
Stdlib only.
"""
from __future__ import annotations
import json, os

def load_flags(path: str):
    if not os.path.isfile(path): return {}
    try: return json.loads(open(path, encoding="utf-8").read())
    except (ValueError, OSError): return {}

def is_enabled(flags: dict, name: str, default: bool = False) -> bool:
    return bool(flags.get(name, default))

class FeatureFlags:
    def __init__(self, path: str = None):
        self.path = path; self._flags = load_flags(path) if path else {}
    def enabled(self, name: str, default: bool = False) -> bool:
        return is_enabled(self._flags, name, default)
    def names(self):
        return list(self._flags.keys())
