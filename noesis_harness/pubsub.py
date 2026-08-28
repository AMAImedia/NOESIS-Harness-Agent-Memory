"""noesis_harness/pubsub.py — publish/subscribe.

Patterns: LoopX pub/sub.
Stdlib only.
"""
from __future__ import annotations
from typing import Callable, Dict, List

class PubSub:
    def __init__(self): self._subs: Dict[str, List[Callable]] = {}
    def subscribe(self, topic: str, fn: Callable) -> None:
        self._subs.setdefault(topic, []).append(fn)
    def publish(self, topic: str, msg) -> int:
        subs = self._subs.get(topic, [])
        for fn in subs: fn(msg)
        return len(subs)
    def topics(self): return list(self._subs.keys())
