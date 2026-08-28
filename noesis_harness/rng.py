"""noesis_harness/rng.py — seeded RNG helpers.

Patterns: LoopX rng.
Stdlib only.
"""
from __future__ import annotations
import random

def make(seed: int) -> random.Random:
    return random.Random(seed)
def randint(r: random.Random, lo: int, hi: int) -> int:
    return r.randint(lo, hi)
def choice(r: random.Random, items: list):
    return r.choice(items)
def shuffle(r: random.Random, items: list) -> list:
    out = list(items); r.shuffle(out); return out
