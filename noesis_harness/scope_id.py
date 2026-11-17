"""Scope namespace as the single isolation key for every harness resource.

Provenance (ported and adapted from the TypeScript repo ``yc-software/qm``):
- ``src/types.ts``: ``scopeId`` / ``parseScopeId`` / ``personalScope`` shape the
  ``kind:ref`` identifier and its validation rules.
- ``src/resolution/resolution-service.ts``: ``conversationScope`` decides whether
  a conversation resolves to a personal scope (DM / no room) or a shared one.
- ``src/workspace/workspace-store.ts``: ``scopeStorageKey`` + ``safeJoin`` motivate
  the deterministic, filesystem-safe ``scope_key`` used to mount a scope on disk.
- ``src/resolution/context-filter.ts``: ``filterHistoryForAudience`` motivates
  ``is_entitled``, the fail-closed audience predicate for history labels.
- ``WorkspaceLayer`` with ``ro`` / ``rw`` modes drives ``layered_workspace``.

This module is deliberately separate from ``noesis_harness/scope.py`` (the
``ScopedMemory`` tenant prefix) and must not be confused with it.

Design goals: pure and side-effect free, stdlib only, deterministic, and
fail-closed. Any malformed scope identifier raises :class:`ScopeError` at the
boundary rather than silently widening access.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

# The only legal leading segments of a scope identifier.
SCOPE_KINDS = ("personal", "channel", "team", "org", "group")

# Ref = the part after ``kind:``. It is opaque except that it may not be empty
# and may not itself contain a colon (which would make parsing ambiguous).
_SAFE_REF = re.compile(r"^[A-Za-z0-9._-]+$")
_SAFE_REF_MAX = 64


class ScopeError(ValueError):
    """Raised when a scope identifier or workspace layer is malformed."""


def parse_scope(scope_id: str) -> Tuple[str, str]:
    """Split ``kind:ref`` into ``(kind, ref)``.

    Raises :class:`ScopeError` when ``scope_id`` is not a string, has no
    colon, has a kind outside :data:`SCOPE_KINDS`, has an empty ref, or has a
    ref that itself contains a colon.
    """
    if not isinstance(scope_id, str):
        raise ScopeError("scope id must be a string")
    if ":" not in scope_id:
        raise ScopeError("scope id must be 'kind:ref'")
    kind, ref = scope_id.split(":", 1)
    if kind not in SCOPE_KINDS:
        raise ScopeError("unknown scope kind: %r" % (kind,))
    if not ref:
        raise ScopeError("scope ref must be non-empty")
    if ":" in ref:
        raise ScopeError("scope ref must not contain ':'")
    return kind, ref


def format_scope(kind: str, ref: str) -> str:
    """Validate and join ``kind`` and ``ref`` into ``kind:ref``."""
    if not isinstance(kind, str) or kind not in SCOPE_KINDS:
        raise ScopeError("unknown scope kind: %r" % (kind,))
    if not isinstance(ref, str) or not ref:
        raise ScopeError("scope ref must be a non-empty string")
    if ":" in ref:
        raise ScopeError("scope ref must not contain ':'")
    return kind + ":" + ref


def personal_scope(actor: str) -> str:
    """Return the personal scope of ``actor``.

    An empty or non-string ``actor`` raises :class:`ScopeError`; there is no
    anonymous personal scope.
    """
    return format_scope("personal", actor)


def conversation_scope(
    actor: str,
    room: Optional[str] = None,
    is_dm: bool = False,
) -> str:
    """Resolve the scope a conversation runs in.

    A direct message (``is_dm=True``) or a missing/empty ``room`` resolves to
    the personal scope of ``actor``. Otherwise the room is shared:

    - a room starting with ``#`` becomes ``channel:<room without '#'>``;
    - a room starting with ``channel:`` becomes ``channel:<room without the prefix>``;
    - any other room becomes ``group:<room>``.

    Malformed input fails closed: an empty ``actor`` raises
    :class:`ScopeError` (via :func:`personal_scope`), and a room that strips
    down to an empty ref, or that already carries a colon it should not, also
    raises :class:`ScopeError`.
    """
    if not isinstance(actor, str) or not actor:
        raise ScopeError("conversation actor must be a non-empty string")
    if is_dm or not room:
        return personal_scope(actor)
    if room.startswith("#"):
        return format_scope("channel", room.lstrip("#"))
    if room.startswith("channel:"):
        return format_scope("channel", room[len("channel:"):])
    return format_scope("group", room)


def _is_safe_ref(ref: str) -> bool:
    """True when ``ref`` may be used verbatim inside a filesystem key."""
    if len(ref) > _SAFE_REF_MAX:
        return False
    if ".." in ref:
        return False
    return _SAFE_REF.match(ref) is not None


def scope_key(scope_id: str) -> str:
    """Return a deterministic, filesystem-safe storage key for ``scope_id``.

    The key is ``kind + "-" + ref`` when ``ref`` is already safe (only
    ``[A-Za-z0-9._-]``, at most 64 characters, no ``..``). Otherwise the key is
    ``kind + "-" + <first 16 hex chars of sha256(ref)>``. The result never
    contains path separators, ``..`` segments, or absolute markers, so it is
    safe to pass to ``os.path.join`` (the ``safeJoin`` analogue).
    """
    kind, ref = parse_scope(scope_id)
    if _is_safe_ref(ref):
        return kind + "-" + ref
    digest = hashlib.sha256(ref.encode("utf-8")).hexdigest()[:16]
    return kind + "-" + digest


@dataclass(frozen=True)
class WorkspaceLayer:
    """One mounted workspace layer bound to a scope.

    ``mode`` is access intent, not enforcement: only ``"ro"`` and ``"rw"`` are
    accepted; anything else raises :class:`ScopeError` at construction.
    """

    scope_id: str
    mount_path: str
    mode: str

    def __post_init__(self) -> None:
        if self.mode not in ("ro", "rw"):
            raise ScopeError("workspace mode must be 'ro' or 'rw'")


def _layer_scope_id(value: str, kind: str) -> str:
    """Treat ``value`` as a full scope id when it has a kind, else as a ref."""
    if isinstance(value, str) and ":" in value:
        return value
    return format_scope(kind, value)


def layered_workspace(
    current: str,
    org: Optional[str] = None,
    team: Optional[str] = None,
    is_dm: bool = False,
) -> List[WorkspaceLayer]:
    """Build the ordered workspace layers for ``current``.

    Order is deterministic: org, then current, then team. The org layer is the
    read-only global mount, the current scope is read-write, and the team layer
    is read-only and is omitted for direct messages. ``org`` / ``team`` may be
    given either as a full scope id or as a bare ref (which is then namespaced).
    """
    layers: List[WorkspaceLayer] = []
    if org is not None:
        org_scope = _layer_scope_id(org, "org")
        layers.append(WorkspaceLayer(org_scope, scope_key(org_scope), "ro"))
    layers.append(WorkspaceLayer(current, scope_key(current), "rw"))
    if team is not None and not is_dm:
        team_scope = _layer_scope_id(team, "team")
        layers.append(WorkspaceLayer(team_scope, scope_key(team_scope), "ro"))
    return layers


def _same_scope(candidate: str, label: str) -> bool:
    """True when ``candidate`` and ``label`` denote the same scope."""
    try:
        return parse_scope(candidate) == parse_scope(label)
    except ScopeError:
        return False


def is_entitled(principal: str, label: str, session_scope: str) -> bool:
    """Decide whether ``principal`` may see a history label.

    Audience rules:

    - ``personal:`` labels are visible only to their owner: the principal must
      be the same personal scope.
    - ``channel:`` / ``group:`` labels are visible to a principal whose scope
      kind and ref match, or when the session scope equals the label.
    - labels of any other kind (``team:`` / ``org:``) are visible.

    Fail-closed: a malformed ``label`` or ``principal`` returns ``False``
    rather than raising or defaulting to visible.
    """
    try:
        principal_kind, principal_ref = parse_scope(principal)
        label_kind, label_ref = parse_scope(label)
    except ScopeError:
        return False
    if label_kind == "personal":
        return principal_kind == "personal" and principal_ref == label_ref
    if label_kind in ("channel", "group"):
        if principal_kind == label_kind and principal_ref == label_ref:
            return True
        return _same_scope(session_scope, label)
    return True


def is_cross_scope(a: str, b: str) -> bool:
    """True when ``a`` and ``b`` do not resolve to the same ``(kind, ref)``.

    Fails closed: an unparseable identifier cannot be proven equal to another,
    so it is treated as cross-scope.
    """
    try:
        return parse_scope(a) != parse_scope(b)
    except ScopeError:
        return True


__all__ = [
    "SCOPE_KINDS",
    "ScopeError",
    "parse_scope",
    "format_scope",
    "personal_scope",
    "conversation_scope",
    "scope_key",
    "WorkspaceLayer",
    "layered_workspace",
    "is_entitled",
    "is_cross_scope",
]
