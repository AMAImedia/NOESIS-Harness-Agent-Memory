"""Signed capability tokens bound to actor, scope, scope version, run and lease.

Provenance: ported from the qm repository (yc-software/qm,
``src/auth/capability-token.ts``). The original pattern issues a compact token
that binds a capability to an actor, a scope, the scope version, a run
identifier and a lease token, and verifies that binding with an HMAC before any
action is authorized. The Go/TypeScript shape is preserved here: one signed
token string, a canonical JSON payload, and a constant-time signature check.

Boundary: this is a local integrity and authorization primitive, NOT a network
authentication system. It proves that a token was produced by a holder of the
shared secret and that the claims inside it were not altered after issuance. It
does not provide confidentiality, key management, replay protection,
revocation, transport security or identity federation; callers own secret
storage, delivery, rotation and lifetime. The module trusts the caller's
process boundary, so it is suitable for gating local tool calls between
cooperating components, not for authenticating untrusted remote peers.

This module is pure and side-effect free. It depends only on the Python
standard library (base64, hashlib, hmac, json, time) so it can be imported
anywhere in the harness, including paths that must stay dependency-free. Given
the same inputs every function returns the same output.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Optional, Tuple

__all__ = [
    "TokenError",
    "Capability",
    "mint_capability",
    "verify_capability",
    "capability_grants",
    "canonical_bytes",
    "b64e",
    "b64d",
]

_TOKEN_PREFIX = "v1"
_PAYLOAD_VERSION = 1
_SHA256_BYTES = 32


class TokenError(RuntimeError):
    """Raised when a capability token is malformed or fails verification.

    A single error type is used on purpose: callers should treat every failure
    as "this token does not authorize the action" without learning which check
    failed, which would otherwise leak information about valid tokens.
    """


def _b64e(data):
    """Return unpadded urlsafe base64 text for ``data``.

    ``data`` must be ``bytes``. Padding is stripped so tokens stay compact and
    free of ``=`` separators that would complicate dotted token framing.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TokenError("base64 encode expects bytes")
    return base64.urlsafe_b64encode(bytes(data)).decode("ascii").rstrip("=")


def _b64d(text):
    """Return the bytes encoded by unpadded urlsafe base64 ``text``.

    Raises :class:`TokenError` when ``text`` is not text or is not valid
    urlsafe base64.
    """
    if not isinstance(text, str):
        raise TokenError("base64 decode expects text")
    if text == "":
        return b""
    padding = "=" * (-len(text) % 4)
    try:
        return base64.urlsafe_b64decode(text + padding)
    except (ValueError, TypeError) as exc:
        raise TokenError("malformed token: invalid base64") from exc


b64e = _b64e
b64d = _b64d


def canonical_bytes(value):
    """Return the canonical UTF-8 JSON encoding of ``value`` as bytes.

    Keys are sorted, separators are compact, non-ASCII characters are preserved
    rather than escaped, and unsupported values are stringified via ``str``.
    The result is deterministic for a given logical value, which is what makes
    the signature stable across processes and machines.
    """
    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return text.encode("utf-8")


@dataclass(frozen=True)
class Capability:
    """A signed claim binding an actor to a scope, run and lease.

    Fields:
    - ``actor``: identity the capability is issued to.
    - ``scope``: resource or capability namespace the grant applies to.
    - ``scope_version``: monotonic version of the scope definition; a bump
      invalidates tokens minted against older definitions.
    - ``run_id``: agent run the capability belongs to.
    - ``lease_token``: short-lived lease the capability is pinned to.
    - ``permissions``: granted permission names. An empty tuple means "no
      permissions": it grants nothing, it does not mean "all".
    - ``issued_at``: Unix seconds when minted (informational).
    - ``expires_at``: Unix seconds after which the token is invalid; ``0``
      means the token has no expiry and never fails the expiry check.
    """

    actor: str
    scope: str
    scope_version: int
    run_id: str
    lease_token: str
    permissions: Tuple[str, ...] = ()
    issued_at: float = 0.0
    expires_at: float = 0.0

    def matches_claim(self, actor, scope, scope_version, run_id, lease_token):
        """Return whether this capability binds the given claim exactly.

        All five bound fields must match. Permissions and timestamps are not
        part of the claim identity and are checked separately.
        """
        return (
            self.actor == actor
            and self.scope == scope
            and self.scope_version == scope_version
            and self.run_id == run_id
            and self.lease_token == lease_token
        )


def _payload_for(capability):
    """Return the signed JSON payload dictionary for ``capability``."""
    return {
        "actor": capability.actor,
        "scope": capability.scope,
        "scope_version": capability.scope_version,
        "run_id": capability.run_id,
        "lease_token": capability.lease_token,
        "permissions": list(capability.permissions),
        "issued_at": capability.issued_at,
        "expires_at": capability.expires_at,
        "v": _PAYLOAD_VERSION,
    }


def mint_capability(secret, capability):
    """Mint a signed token string for ``capability`` using ``secret``.

    The token has the form ``v1.<payload>.<signature>`` where both segments are
    unpadded urlsafe base64. The signature is HMAC-SHA256 over the exact bytes
    of the canonical payload, so verification does not depend on re-serializing
    the JSON.
    """
    if not isinstance(secret, (bytes, bytearray)):
        raise TokenError("secret must be bytes")
    payload_bytes = canonical_bytes(_payload_for(capability))
    signature = hmac.new(bytes(secret), payload_bytes, hashlib.sha256).digest()
    return _TOKEN_PREFIX + "." + b64e(payload_bytes) + "." + b64e(signature)


def _capability_from_payload(raw):
    """Build a :class:`Capability` from a verified payload dictionary."""

    def require(key):
        if key not in raw:
            raise TokenError("malformed token: missing field %s" % key)
        return raw[key]

    actor = require("actor")
    scope = require("scope")
    scope_version = require("scope_version")
    run_id = require("run_id")
    lease_token = require("lease_token")
    permissions = raw.get("permissions", [])
    issued_at = raw.get("issued_at", 0.0)
    expires_at = raw.get("expires_at", 0.0)

    if not isinstance(actor, str) or not isinstance(scope, str):
        raise TokenError("malformed token: actor and scope must be text")
    if not isinstance(run_id, str) or not isinstance(lease_token, str):
        raise TokenError("malformed token: run_id and lease_token must be text")
    if not isinstance(scope_version, int) or isinstance(scope_version, bool):
        raise TokenError("malformed token: scope_version must be an integer")
    if not isinstance(permissions, (list, tuple)):
        raise TokenError("malformed token: permissions must be a list")
    for permission in permissions:
        if not isinstance(permission, str):
            raise TokenError("malformed token: permissions must be text")
    if not isinstance(issued_at, (int, float)) or isinstance(issued_at, bool):
        raise TokenError("malformed token: issued_at must be numeric")
    if not isinstance(expires_at, (int, float)) or isinstance(expires_at, bool):
        raise TokenError("malformed token: expires_at must be numeric")

    return Capability(
        actor=actor,
        scope=scope,
        scope_version=scope_version,
        run_id=run_id,
        lease_token=lease_token,
        permissions=tuple(permissions),
        issued_at=float(issued_at),
        expires_at=float(expires_at),
    )


def verify_capability(secret, token, now=None):
    """Verify ``token`` and return the :class:`Capability` it carries.

    Raises :class:`TokenError` when the token is malformed, the signature does
    not match (compared in constant time with :func:`hmac.compare_digest`), the
    payload version is not supported, the payload fields have the wrong shape,
    or the token is expired. Expiry uses ``now`` (Unix seconds) when supplied
    and the wall clock otherwise; a token with ``expires_at == 0`` never
    expires.
    """
    if not isinstance(secret, (bytes, bytearray)):
        raise TokenError("secret must be bytes")
    if not isinstance(token, str):
        raise TokenError("malformed token: not a string")
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != _TOKEN_PREFIX:
        raise TokenError("malformed token: unexpected framing")
    payload_bytes = b64d(parts[1])
    provided_signature = b64d(parts[2])
    expected_signature = hmac.new(
        bytes(secret), payload_bytes, hashlib.sha256
    ).digest()
    if not hmac.compare_digest(provided_signature, expected_signature):
        raise TokenError("capability signature mismatch")

    try:
        raw = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise TokenError("malformed token: payload is not JSON") from exc
    if not isinstance(raw, dict):
        raise TokenError("malformed token: payload is not an object")

    if raw.get("v") != _PAYLOAD_VERSION:
        raise TokenError("unsupported capability version")

    capability = _capability_from_payload(raw)

    if capability.expires_at != 0:
        current = time.time() if now is None else now
        if current > capability.expires_at:
            raise TokenError("capability expired")
    return capability


def capability_grants(secret, token, required_claim, permission, now=None):
    """Return whether ``token`` grants ``permission`` for ``required_claim``.

    The token is first verified (signature, version, expiry). Then the token's
    binding must exactly match the actor, scope, scope version, run and lease in
    ``required_claim``. Finally ``permission`` must appear in the token's
    permissions. An empty permission tuple grants nothing, so any query against
    such a token returns ``False``.

    This function is total: any verification failure (malformed token, bad
    signature, unsupported version, expiry) yields ``False`` rather than
    propagating :class:`TokenError`, because it is a boolean authorization
    predicate. Use :func:`verify_capability` directly when the reason for
    failure matters.
    """
    try:
        capability = verify_capability(secret, token, now=now)
    except TokenError:
        return False
    if not capability.matches_claim(
        required_claim.actor,
        required_claim.scope,
        required_claim.scope_version,
        required_claim.run_id,
        required_claim.lease_token,
    ):
        return False
    return permission in capability.permissions
