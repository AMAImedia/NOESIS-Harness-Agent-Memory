"""Deterministic hook engine with a preview/run split.

Provenance (patterns ported, not copied verbatim):
- harness-books, book2 chapter-05 "skills-hooks-and-local-governance": the
  Claude Code hook surface (pre/post tool, session start/end, pre-compact,
  subagent start/stop) and the idea that a hook registry can answer two
  different questions -- "what WOULD run, in what order" (a dry run / preview)
  and "run it now" (fire). The split lets an operator audit ordering and
  disabled state without executing any callback.
- The stable ``display_order`` field mirrors the book's replayable ordering:
  hooks are surfaced by ``(display_order, name)`` so two runs over the same
  registry produce the same sequence, and ties are broken by a stable key
  rather than registration order.

This module is an in-memory registry only. It never touches disk, never
spawns processes, and never calls an LLM. Ordering and results are
deterministic: the only non-deterministic value is ``duration_s``, which stays
at ``0.0`` unless a caller injects an explicit timer. A failing hook is
captured as ``HookResult(ok=False)`` and never stops the remaining hooks; every
hook receives its own deep copy of the payload so one hook cannot mutate what
the next one sees.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional

__all__ = [
    "HookEvent",
    "HookResult",
    "Hook",
    "HookEngine",
    "HookBudgetError",
]


class HookEvent(str, Enum):
    """The Claude Code hook surface.

    Values are lowercase strings so they round-trip through logs and receipts
    without a separate serializer.
    """

    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    PRE_COMPACT = "pre_compact"
    SUBAGENT_START = "subagent_start"
    SUBAGENT_STOP = "subagent_stop"


@dataclass(frozen=True)
class HookResult:
    """Outcome of a single hook invocation.

    A raised exception is flattened into ``ok=False`` with ``output`` set to
    ``str(exc)``; nothing is re-raised from ``fire``.
    """

    hook: str
    event: HookEvent
    ok: bool
    output: str
    duration_s: float = 0.0


@dataclass
class Hook:
    """A registered callback bound to one event.

    ``display_order`` is the primary sort key for replayable ordering; ``name``
    breaks ties. ``name`` must be a non-empty string.
    """

    name: str
    event: HookEvent
    callback: Callable[[Dict], str]
    display_order: int = 0
    enabled: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("hook_name_invalid")
        if not isinstance(self.event, HookEvent):
            raise ValueError("hook_event_invalid")
        if not callable(self.callback):
            raise ValueError("hook_callback_not_callable")
        if isinstance(self.display_order, bool) or not isinstance(self.display_order, int):
            raise ValueError("hook_display_order_invalid")


class HookBudgetError(RuntimeError):
    """Raised before running when an event exceeds the enabled-hook budget."""


class HookEngine:
    """In-memory registry of hooks with preview/fire and stable ordering.

    Args:
        max_hooks: maximum number of *enabled* hooks allowed for a single
            event. ``fire`` refuses to run (raising ``HookBudgetError``) when
            the count would exceed this. Defaults to 32.
        timer: optional zero-argument callable returning a monotonic float.
            When provided it is used to populate ``HookResult.duration_s``;
            when omitted all durations stay ``0.0`` (fully deterministic).
    """

    def __init__(self, max_hooks: int = 32,
                 timer: Optional[Callable[[], float]] = None) -> None:
        if isinstance(max_hooks, bool) or not isinstance(max_hooks, int):
            raise ValueError("hook_max_hooks_invalid")
        if max_hooks < 1:
            raise ValueError("hook_max_hooks_invalid")
        self._max_hooks = max_hooks
        self._timer = timer
        self._hooks: Dict[str, Hook] = {}
        self._results: List[HookResult] = []

    def register(self, hook: Hook) -> None:
        """Add a hook. Raises ValueError on a duplicate name."""
        if not isinstance(hook, Hook):
            raise ValueError("hook_invalid")
        if hook.name in self._hooks:
            raise ValueError("hook_duplicate_name: " + hook.name)
        self._hooks[hook.name] = hook

    def hooks(self, event: Optional[HookEvent] = None) -> List[Hook]:
        """Return registered hooks sorted by (display_order, name).

        When ``event`` is given, only hooks bound to that event are returned.
        Both enabled and disabled hooks are included; filter on ``.enabled``
        for a run set.
        """
        values = list(self._hooks.values())
        if event is not None:
            values = [hook for hook in values if hook.event == event]
        return sorted(values, key=lambda hook: (hook.display_order, hook.name))

    def preview(self, event: HookEvent,
                payload: Optional[Dict] = None) -> List[Dict]:
        """Dry run: list what WOULD run, in order, without calling callbacks.

        Only enabled hooks appear. ``payload`` is accepted for signature
        symmetry with ``fire`` and is never read. Each item carries the keys
        ``name``, ``display_order`` and ``event``.
        """
        items: List[Dict] = []
        for hook in self._enabled_for(event):
            items.append({
                "name": hook.name,
                "display_order": hook.display_order,
                "event": hook.event,
            })
        return items

    def fire(self, event: HookEvent,
             payload: Optional[Dict] = None) -> List[HookResult]:
        """Run enabled hooks for ``event`` in stable order.

        Raises ``HookBudgetError`` before running anything when the number of
        enabled hooks for the event exceeds ``max_hooks``. A hook that raises
        yields ``HookResult(ok=False, output=str(exc))`` and does not stop the
        rest. Each hook receives a deep copy of ``payload`` so hooks cannot
        mutate each other's view.
        """
        enabled = self._enabled_for(event)
        if len(enabled) > self._max_hooks:
            raise HookBudgetError(
                "hook_budget_exceeded: event=%s enabled=%d max=%d"
                % (event.value, len(enabled), self._max_hooks)
            )

        base: Dict = {} if payload is None else payload
        results: List[HookResult] = []
        for hook in enabled:
            local_payload = copy.deepcopy(base)
            started = self._timer() if self._timer is not None else None
            try:
                raw = hook.callback(local_payload)
                ok = True
                output = "" if raw is None else str(raw)
            except Exception as exc:  # noqa: BLE001 - failures must not cascade
                ok = False
                output = str(exc)
            duration_s = 0.0
            if self._timer is not None:
                duration_s = float(self._timer() - started)
            results.append(HookResult(
                hook=hook.name,
                event=event,
                ok=ok,
                output=output,
                duration_s=duration_s,
            ))

        self._results = results
        return list(results)

    def last_results(self) -> List[HookResult]:
        """Return a copy of the results from the most recent ``fire``."""
        return list(self._results)

    def disable(self, name: str) -> bool:
        """Disable a hook by name. Returns False when the name is unknown."""
        hook = self._hooks.get(name)
        if hook is None:
            return False
        hook.enabled = False
        return True

    def enable(self, name: str) -> bool:
        """Enable a hook by name. Returns False when the name is unknown."""
        hook = self._hooks.get(name)
        if hook is None:
            return False
        hook.enabled = True
        return True

    def clear(self) -> None:
        """Unregister all hooks and reset the last-results buffer.

        In-memory only; nothing on disk is touched.
        """
        self._hooks.clear()
        self._results = []

    def _enabled_for(self, event: HookEvent) -> List[Hook]:
        return [hook for hook in self.hooks(event) if hook.enabled]
