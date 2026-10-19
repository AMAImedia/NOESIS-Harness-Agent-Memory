"""Explicit ACL grant store with owner-scoped grants and no transitive re-share.

Provenance (ported and adapted from the TypeScript repo ``yc-software/qm``):
- ``src/acl/acl-store.ts``: the grant record
  ``{ownerScopeId, ref, granteeScopeId, permission}``, owner-scoped grant
  storage, membership management, and the invariant that only the owner of a
  resource may issue grants on it (a grantee can never re-share transitively).

Adaptation notes:
- The original store is reachable through a live backing store; this port is a
  pure in-memory, stdlib-only model that can be serialized with ``to_json`` and
  restored with ``from_json``.
- Ownership is inferred from the first grant made on a ``ref``. Once a ``ref``
  has an owner, any grant attempt from a different ``owner_scope`` fails closed
  with :class:`AclError`; this is what makes transitive re-share impossible
  rather than merely ignored.
- Permissions are totally ordered ``READ < WRITE < ADMIN``. Re-granting may
  only move a grantee upward; an implicit downgrade is ignored and an explicit
  downgrade requires :meth:`AclStore.revoke` followed by a fresh grant.
- Membership is itself fail-closed: an unknown scope has no members, so
  :meth:`MembershipAcl.can_member` returns ``False`` rather than raising.

Design goals: stdlib only, deterministic, no global mutable state, and
fail-closed on malformed input.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class Permission(str, Enum):
    """Access level, totally ordered ``READ < WRITE < ADMIN``."""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Permission):
            return NotImplemented
        return _rank(self) < _rank(other)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Permission):
            return NotImplemented
        return _rank(self) <= _rank(other)

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Permission):
            return NotImplemented
        return _rank(self) > _rank(other)

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Permission):
            return NotImplemented
        return _rank(self) >= _rank(other)


_RANK: Dict[Permission, int] = {
    Permission.READ: 0,
    Permission.WRITE: 1,
    Permission.ADMIN: 2,
}


def _rank(permission: Permission) -> int:
    """Return the total-order rank of ``permission``."""
    return _RANK[permission]


class AclError(RuntimeError):
    """Raised when an ACL operation violates the grant contract."""


@dataclass(frozen=True)
class Grant:
    """One explicit owner-scoped grant of ``ref`` to ``grantee_scope``.

    All string fields must be non-empty; ``permission`` must be a
    :class:`Permission`. Invalid input raises :class:`ValueError` at
    construction time.
    """

    owner_scope: str
    ref: str
    grantee_scope: str
    permission: Permission

    def __post_init__(self) -> None:
        for name in ("owner_scope", "ref", "grantee_scope"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError("%s must be a non-empty string" % name)
        if not isinstance(self.permission, Permission):
            raise ValueError("permission must be a Permission")


class AclStore:
    """Owner-scoped, non-transitive grant store.

    Ownership of a ``ref`` is claimed by the owner scope of its first grant and
    is permanent for the lifetime of the store (revoking grants does not
    relinquish ownership, so the owner keeps ADMIN access).
    """

    def __init__(self) -> None:
        self._grants: Dict[Tuple[str, str, str], Permission] = {}
        self._owners: Dict[str, str] = {}

    def grant(
        self,
        owner_scope: str,
        ref: str,
        grantee_scope: str,
        permission: Permission,
    ) -> Grant:
        """Create or raise a grant on ``ref`` and return the effective grant.

        Raises :class:`AclError` when ``permission`` is not a
        :class:`Permission`, when the owner tries to grant to itself, or when a
        different scope attempts to grant on a ``ref`` already owned by another
        scope (no transitive re-share). Re-granting never downgrades
        implicitly: the effective permission is the maximum of the existing and
        requested levels.
        """
        if not isinstance(permission, Permission):
            raise AclError("permission must be a Permission")
        if owner_scope == grantee_scope:
            raise AclError("owner may not grant to itself")
        candidate = Grant(owner_scope, ref, grantee_scope, permission)
        existing_owner = self._owners.get(candidate.ref)
        if existing_owner is None:
            self._owners[candidate.ref] = candidate.owner_scope
        elif existing_owner != candidate.owner_scope:
            raise AclError("only the owner of a ref may grant on it")
        key = (candidate.owner_scope, candidate.ref, candidate.grantee_scope)
        current = self._grants.get(key)
        if current is None or _rank(candidate.permission) > _rank(current):
            self._grants[key] = candidate.permission
        return Grant(
            candidate.owner_scope,
            candidate.ref,
            candidate.grantee_scope,
            self._grants[key],
        )

    def revoke(self, owner_scope: str, ref: str, grantee_scope: str) -> bool:
        """Remove one grant, returning ``True`` when a grant was present."""
        return self._grants.pop((owner_scope, ref, grantee_scope), None) is not None

    def can(self, principal: str, ref: str, required: Permission) -> bool:
        """Return whether ``principal`` holds at least ``required`` on ``ref``.

        The owner is always allowed (ADMIN). A grantee is allowed only from the
        current owner's grant and only when their permission is at least
        ``required``. Grants can never be re-shared transitively.
        """
        if not isinstance(required, Permission):
            return False
        if self._owners.get(ref) == principal:
            return True
        permission = self._permission_from_owner(principal, ref)
        if permission is None:
            return False
        return _rank(permission) >= _rank(required)

    def permission_for(self, principal: str, ref: str) -> Optional[Permission]:
        """Return the effective permission of ``principal`` on ``ref``.

        The owner always resolves to :data:`Permission.ADMIN`; a grantee
        resolves to the stored permission; everyone else resolves to ``None``.
        """
        if self._owners.get(ref) == principal:
            return Permission.ADMIN
        return self._permission_from_owner(principal, ref)

    def grants(self, ref: Optional[str] = None) -> List[Grant]:
        """Return grants sorted by ``(owner_scope, ref, grantee_scope)``.

        When ``ref`` is given, only grants on that ref are returned.
        """
        result: List[Grant] = []
        for (owner_scope, grant_ref, grantee_scope), permission in self._grants.items():
            if ref is not None and grant_ref != ref:
                continue
            result.append(Grant(owner_scope, grant_ref, grantee_scope, permission))
        result.sort(key=lambda item: (item.owner_scope, item.ref, item.grantee_scope))
        return result

    def revoke_all_for(self, grantee_scope: str) -> int:
        """Revoke every grant held by ``grantee_scope`` and return the count."""
        keys = [key for key in self._grants if key[2] == grantee_scope]
        for key in keys:
            del self._grants[key]
        return len(keys)

    def owners(self) -> List[str]:
        """Return the sorted distinct owner scopes that ever claimed a ref."""
        return sorted(set(self._owners.values()))

    def grantees(self) -> List[str]:
        """Return the sorted distinct grantee scopes with a live grant."""
        return sorted({key[2] for key in self._grants})

    def to_json(self) -> str:
        """Serialize the store to deterministic, compact JSON."""
        payload = {
            "version": 1,
            "owners": {ref: self._owners[ref] for ref in sorted(self._owners)},
            "grants": [
                {
                    "owner_scope": grant.owner_scope,
                    "ref": grant.ref,
                    "grantee_scope": grant.grantee_scope,
                    "permission": grant.permission.value,
                }
                for grant in self.grants()
            ],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, text: str) -> "AclStore":
        """Rebuild a store from :meth:`to_json` output.

        Malformed JSON, an inconsistent owner mapping, or an unknown permission
        raises :class:`AclError`.
        """
        try:
            payload = json.loads(text)
        except (TypeError, ValueError) as exc:
            raise AclError("invalid acl json: %s" % exc)
        if not isinstance(payload, dict):
            raise AclError("acl json must be an object")
        store = cls()
        owners = payload.get("owners", {})
        if owners is not None and not isinstance(owners, dict):
            raise AclError("acl json owners must be an object")
        if isinstance(owners, dict):
            for ref, owner in owners.items():
                if not isinstance(ref, str) or not ref:
                    raise AclError("acl json owner ref must be a non-empty string")
                if not isinstance(owner, str) or not owner:
                    raise AclError("acl json owner must be a non-empty string")
                store._owners[ref] = owner
        grant_items = payload.get("grants", [])
        if grant_items is None:
            grant_items = []
        if not isinstance(grant_items, list):
            raise AclError("acl json grants must be a list")
        for item in grant_items:
            if not isinstance(item, dict):
                raise AclError("acl json grant must be an object")
            try:
                permission = Permission(item["permission"])
            except KeyError as exc:
                raise AclError("acl json grant missing permission: %s" % exc)
            except ValueError as exc:
                raise AclError("acl json grant has unknown permission: %s" % exc)
            try:
                grant = Grant(
                    item.get("owner_scope", ""),
                    item.get("ref", ""),
                    item.get("grantee_scope", ""),
                    permission,
                )
            except ValueError as exc:
                raise AclError("acl json grant is invalid: %s" % exc)
            existing_owner = store._owners.get(grant.ref)
            if existing_owner is None:
                store._owners[grant.ref] = grant.owner_scope
            elif existing_owner != grant.owner_scope:
                raise AclError("acl json grant owner does not match ref owner")
            store._grants[(grant.owner_scope, grant.ref, grant.grantee_scope)] = (
                grant.permission
            )
        return store

    def _permission_from_owner(
        self, principal: str, ref: str
    ) -> Optional[Permission]:
        """Return the grant permission only when the owner issued it.

        Grants are keyed by their issuing owner; a grant can therefore never be
        used to authorize a third party because only the recorded owner of the
        ``ref`` is ever consulted here.
        """
        owner = self._owners.get(ref)
        if owner is None:
            return None
        return self._grants.get((owner, ref, principal))


class Membership:
    """Fail-closed scope membership registry."""

    def __init__(self) -> None:
        self._members: Dict[str, set] = {}

    @staticmethod
    def _require(value: str, name: str) -> None:
        if not isinstance(value, str) or not value:
            raise ValueError("%s must be a non-empty string" % name)

    def add(self, scope: str, member: str) -> None:
        """Add ``member`` to ``scope`` (idempotent)."""
        self._require(scope, "scope")
        self._require(member, "member")
        self._members.setdefault(scope, set()).add(member)

    def remove(self, scope: str, member: str) -> bool:
        """Remove ``member`` from ``scope``, returning ``True`` if present."""
        members = self._members.get(scope)
        if not members or member not in members:
            return False
        members.discard(member)
        if not members:
            del self._members[scope]
        return True

    def members(self, scope: str) -> List[str]:
        """Return the sorted members of ``scope``; unknown scopes are empty."""
        return sorted(self._members.get(scope, ()))

    def is_member(self, scope: str, member: str) -> bool:
        """Return whether ``member`` belongs to ``scope``."""
        return member in self._members.get(scope, ())


class MembershipAcl(AclStore):
    """ACL store that also answers membership-scoped authorization."""

    def __init__(self) -> None:
        super().__init__()
        self._membership = Membership()

    def can_member(
        self,
        scope: str,
        member: str,
        ref: str,
        required: Permission,
    ) -> bool:
        """Return whether ``member`` of ``scope`` may access ``ref``.

        Fails closed: an unknown scope or a non-member returns ``False``; a
        known member is allowed only when ``scope`` itself holds at least
        ``required`` on ``ref``.
        """
        if not self._membership.is_member(scope, member):
            return False
        return self.can(scope, ref, required)


__all__ = [
    "Permission",
    "Grant",
    "AclError",
    "AclStore",
    "Membership",
    "MembershipAcl",
]
