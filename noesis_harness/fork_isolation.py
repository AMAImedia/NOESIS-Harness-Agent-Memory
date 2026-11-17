"""Fork-isolated sub-context scheduling for multi-agent delegation.

Ports the "fork sub-context" pattern: a forked child runs behind an isolation
boundary. It is isolated by default and shares state with its parent only
through an explicit opt-in share set. A parent abort cascades bottom-up and
leaves no orphaned descendants. Results travel through a one-way channel that
never exposes the child's internal state. A cache-safe parent snapshot keeps
the fork byte-stable so shared-prefix prompt caches stay valid.

Patterns adapted from:
- harness-books, book1 chapter-07 (multi-agent-and-verification):
  ``forkAgent`` invariants, ``createSubagentContext``, cascade close.
- claude-code-book, Part-3 chapters 09/10 and Part-4 chapter 14:
  ``createSubagentContext`` isolation and result envelope.

This module only schedules an injected Python callback. It never executes
model output and never runs tools. It is deterministic and depends only on the
Python standard library.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, FrozenSet, Iterable, List, Optional, Tuple


class Status(str, Enum):
    """Lifecycle status of a forked child scope."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL_STATUSES = frozenset(
    (Status.COMPLETED, Status.FAILED, Status.CANCELLED)
)


class ForkError(RuntimeError):
    """Raised for invalid fork operations and isolation violations."""


def canonical_digest(value: Any) -> str:
    """Return a stable ``sha256:`` digest over the canonical form of ``value``.

    The value is serialized with sorted keys, ``ensure_ascii=False`` and a
    ``str`` fallback for non-JSON types, so equal content always yields the
    same digest regardless of dict insertion order or object identity.
    """
    serialized = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return "sha256:" + digest


@dataclass(frozen=True)
class CacheSafeSnapshot:
    """Immutable parent context snapshot used to keep a fork cache-safe.

    Two forks of the same parent may only proceed when their snapshot is
    byte-stable equal to the parent's registered snapshot. ``messages_digest``
    is computed from the message list with :func:`canonical_digest`.
    """

    system_prompt: str
    user_context: str
    system_context: str
    tool_keys: Tuple[str, ...]
    messages_digest: str

    @classmethod
    def from_messages(
        cls,
        system_prompt: str,
        user_context: str,
        system_context: str,
        tool_keys: Iterable[str],
        messages: List[Any],
    ) -> "CacheSafeSnapshot":
        """Build a snapshot, computing ``messages_digest`` canonically."""
        return cls(
            system_prompt=system_prompt,
            user_context=user_context,
            system_context=system_context,
            tool_keys=tuple(str(key) for key in tool_keys),
            messages_digest=canonical_digest(messages),
        )


class ChildScope:
    """An isolated child execution scope returned by a fork.

    The scope starts with a read-only clone of the parent state. Writes are
    allowed only for keys named in the explicit share set. Once the scope
    reaches a terminal status, all further writes raise :class:`ForkError`.
    """

    def __init__(
        self,
        agent_id: str,
        parent_id: Optional[str],
        shared: Iterable[str],
        parent_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.agent_id = agent_id
        self.parent_id = parent_id
        self.status = Status.CREATED
        self.result: Any = None
        self.error: Optional[str] = None
        self.shared: FrozenSet[str] = frozenset(str(key) for key in shared)
        self._state: Dict[str, Any] = dict(parent_state or {})

    def set_state(self, key: str, value: Any) -> None:
        """Set a shared state key, or raise when it is not opted in."""
        if self.is_terminal():
            raise ForkError("scope is terminal; state writes are closed")
        if key not in self.shared:
            raise ForkError("state key is not shared: %s" % key)
        self._state[key] = value

    def get_state(self, key: str) -> Any:
        """Return a state value, or ``None`` when the key is absent."""
        return self._state.get(key)

    def complete(self, result: Any) -> None:
        """Mark the scope COMPLETED. Idempotent once completed."""
        if self.status is Status.COMPLETED:
            return
        if self.is_terminal():
            return
        self.result = result
        self.status = Status.COMPLETED

    def fail(self, error: str) -> None:
        """Mark the scope FAILED with the given error text."""
        self.error = error
        self.status = Status.FAILED

    def cancel(self) -> None:
        """Mark the scope CANCELLED."""
        self.status = Status.CANCELLED

    def is_terminal(self) -> bool:
        """Return True when the scope can no longer run."""
        return self.status in _TERMINAL_STATUSES


class ForkCoordinator:
    """Schedule isolated child scopes and own the fork lineage."""

    def __init__(self) -> None:
        self._nodes: Dict[str, ChildScope] = {}
        self._parent_snapshots: Dict[Optional[str], CacheSafeSnapshot] = {}
        self._counter = 0

    def register_parent(self, agent_id: str, snapshot: CacheSafeSnapshot) -> None:
        """Register the cache-safe snapshot a parent must fork with."""
        existing = self._parent_snapshots.get(agent_id)
        if existing is not None and existing != snapshot:
            raise ForkError("CacheSafeParams must equal the parent's")
        self._parent_snapshots[agent_id] = snapshot

    def _check_cache_safe(
        self, parent_id: Optional[str], snapshot: CacheSafeSnapshot
    ) -> None:
        existing = self._parent_snapshots.get(parent_id)
        if existing is None:
            self._parent_snapshots[parent_id] = snapshot
            return
        if existing != snapshot:
            raise ForkError("CacheSafeParams must equal the parent's")

    def fork(
        self,
        parent_id: Optional[str],
        cache_safe: CacheSafeSnapshot,
        run: Callable[[ChildScope], Any],
        share: Iterable[str] = (),
    ) -> ChildScope:
        """Create an isolated child, run ``run``, and capture its outcome."""
        if parent_id is not None and parent_id not in self._nodes:
            raise ForkError("unknown parent: %s" % parent_id)
        if not isinstance(cache_safe, CacheSafeSnapshot):
            raise ForkError("cache_safe must be a CacheSafeSnapshot")
        if not callable(run):
            raise ForkError("run must be callable")
        self._check_cache_safe(parent_id, cache_safe)
        parent_state: Dict[str, Any] = {}
        if parent_id is not None:
            parent_state = self._nodes[parent_id]._state
        self._counter += 1
        agent_id = "fork-%d" % self._counter
        scope = ChildScope(agent_id, parent_id, share, parent_state)
        self._nodes[agent_id] = scope
        scope.status = Status.RUNNING
        try:
            outcome = run(scope)
        except Exception as exc:
            scope.fail("%s: %s" % (type(exc).__name__, exc))
        else:
            if not scope.is_terminal():
                scope.complete(outcome)
        return scope

    def children(self, parent_id: Optional[str] = None) -> List[str]:
        """Return the sorted direct child ids of ``parent_id``."""
        return sorted(
            agent_id
            for agent_id, scope in self._nodes.items()
            if scope.parent_id == parent_id
        )

    def _descendants(self, agent_id: str) -> List[str]:
        collected: List[str] = []
        for child_id in self.children(agent_id):
            collected.extend(self._descendants(child_id))
        return collected

    def cancel_subtree(
        self, agent_id: str, cascade: bool = True
    ) -> List[str]:
        """Cancel a node and, when cascading, all descendants bottom-up."""
        if agent_id not in self._nodes:
            raise ForkError("unknown agent: %s" % agent_id)
        cancelled: List[str] = []

        def _cancel(node_id: str, recurse: bool) -> None:
            if recurse:
                for child_id in self.children(node_id):
                    _cancel(child_id, True)
            self._nodes[node_id].cancel()
            cancelled.append(node_id)

        _cancel(agent_id, bool(cascade))
        return sorted(cancelled)

    def result_channel(self, agent_id: str) -> Dict[str, Any]:
        """Return the one-way result envelope for a completed child.

        The envelope exposes only the identity, status, result and error. It
        never exposes the child's internal state.
        """
        scope = self._nodes.get(agent_id)
        if scope is None:
            raise ForkError("unknown agent: %s" % agent_id)
        return {
            "agent_id": scope.agent_id,
            "status": scope.status.value,
            "result": scope.result,
            "error": scope.error,
        }


__all__ = [
    "Status",
    "ForkError",
    "canonical_digest",
    "CacheSafeSnapshot",
    "ChildScope",
    "ForkCoordinator",
]
