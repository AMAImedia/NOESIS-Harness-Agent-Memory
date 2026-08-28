"""noesis_harness/scope_guard.py

Scope isolation for harness operations via a reentrant context manager.

Lets a section of code run under a named scope without mutating any global
harness state. The active scope lives only in a thread-local stack owned by the
guard itself, so the rest of the harness is untouched.

Pattern adapted from LoopX scope isolation (per-agent execution frame
isolation): each entry pushes a scope frame, each exit pops it, and the
currently active scope is whatever sits on top of the stack.

Stdlib only. Deterministic. No LLM, no network, no global harness mutation.
"""

from __future__ import annotations

import threading


class ScopeGuard:
    """Reentrant scope isolation context manager.

    Usage:
        with ScopeGuard("render") as s:
            assert ScopeGuard.current() == "render"
        assert ScopeGuard.current() is None
    """

    _stack = threading.local()

    def __init__(self, scope):
        if scope is None or not isinstance(scope, str) or scope == "":
            raise ValueError("scope_guard_scope_invalid")
        self.scope = scope
        self._entered = False
        self._exited = False

    @classmethod
    def _frames(cls):
        if not hasattr(cls._stack, "frames"):
            cls._stack.frames = []
        return cls._stack.frames

    def __enter__(self):
        if self._entered:
            raise RuntimeError("scope_guard_reentrant_enter")
        self._entered = True
        self._exited = False
        self._frames().append(self.scope)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._entered or self._exited:
            raise RuntimeError("scope_guard_exit_without_enter")
        self._exited = True
        frames = self._frames()
        if not frames or frames[-1] != self.scope:
            raise RuntimeError("scope_guard_stack_corrupt")
        frames.pop()
        return False

    @classmethod
    def current(cls):
        frames = cls._frames()
        if not frames:
            return None
        return frames[-1]

    @classmethod
    def depth(cls):
        return len(cls._frames())
