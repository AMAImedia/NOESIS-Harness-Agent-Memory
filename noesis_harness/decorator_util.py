"""noesis_harness/decorator_util.py — decorator helpers.

Patterns: LoopX decorator.
Stdlib only.
"""
from __future__ import annotations
from typing import Callable

def wrap(fn: Callable, before: Callable = None, after: Callable = None) -> Callable:
    def wrapper(*args, **kwargs):
        if before: before()
        result = fn(*args, **kwargs)
        if after: after()
        return result
    return wrapper
def call_counter(fn: Callable) -> Callable:
    fn._calls = getattr(fn, "_calls", 0) + 1
    return fn
def once(fn: Callable) -> Callable:
    called = [False]; result = [None]
    def wrapper():
        if not called[0]: result[0] = fn(); called[0] = True
        return result[0]
    return wrapper
