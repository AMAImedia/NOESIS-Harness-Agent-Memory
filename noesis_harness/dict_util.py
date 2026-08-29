"""noesis_harness/dict_util.py — dict helpers.

Patterns: LoopX dict util.
Stdlib only.
"""
from __future__ import annotations
from typing import Any

def get_nested(d: dict, path: str, default=None, sep: str = "."):
    keys = path.split(sep)
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur: cur = cur[k]
        else: return default
    return cur
def set_nested(d: dict, path: str, value, sep: str = ".") -> None:
    keys = path.split(sep); cur = d
    for k in keys[:-1]:
        if k not in cur or not isinstance(cur[k], dict): cur[k] = {}
        cur = cur[k]
    cur[keys[-1]] = value
def pick(d: dict, keys: list) -> dict:
    return {k: d[k] for k in keys if k in d}
def omit(d: dict, keys: list) -> dict:
    return {k: v for k, v in d.items() if k not in keys}
def invert(d: dict) -> dict:
    return {v: k for k, v in d.items()}
