"""Provider-neutral external identity preparation for administrative authorization.

The module validates already-decoded claims only. It deliberately does not fetch,
verify, or refresh tokens and therefore cannot claim external provider execution.
A deployment may inject a provider-specific verifier at the boundary later.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .promotion_integration import OperatorAuthContext

SCHEMA_VERSION = "noesis.external-identity-preparation.v1"


class ExternalIdentityPreparationError(ValueError):
    """Raised when external identity claims are missing, stale, or out of scope."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PreparedExternalIdentity:
    issuer: str
    subject: str
    audience: tuple[str, ...]
    scopes: tuple[str, ...]
    expires_at: float
    claims_digest: str
    schema_version: str = SCHEMA_VERSION

    def context(self, session_id: str) -> OperatorAuthContext:
        if not session_id:
            raise ExternalIdentityPreparationError("operator_session_id_required")
        return OperatorAuthContext(self.subject, str(session_id), self.scopes, authenticated=True)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "issuer": self.issuer,
            "subject": self.subject,
            "audience": list(self.audience),
            "scopes": list(self.scopes),
            "expires_at": self.expires_at,
            "claims_digest": self.claims_digest,
        }


class ExternalIdentityPreparation:
    """Validate claims at the provider boundary while remaining provider-neutral."""

    def __init__(self, *, trusted_issuers: Sequence[str], expected_audience: str, clock: Callable[[], float] = time.time, max_clock_skew_seconds: float = 30.0) -> None:
        issuers = tuple(sorted({str(item) for item in trusted_issuers if str(item)}))
        if not issuers or not expected_audience:
            raise ValueError("external_identity_configuration_required")
        if max_clock_skew_seconds < 0 or max_clock_skew_seconds > 86400:
            raise ValueError("invalid_identity_clock_skew")
        self.trusted_issuers = issuers
        self.expected_audience = str(expected_audience)
        self.clock = clock
        self.max_clock_skew_seconds = float(max_clock_skew_seconds)

    def prepare(self, claims: Mapping[str, Any], *, required_scopes: Sequence[str] = ()) -> PreparedExternalIdentity:
        if not isinstance(claims, Mapping):
            raise ExternalIdentityPreparationError("external_claims_mapping_required")
        issuer = str(claims.get("iss", ""))
        subject = str(claims.get("sub", ""))
        if issuer not in self.trusted_issuers:
            raise ExternalIdentityPreparationError("external_identity_issuer_denied")
        if not subject:
            raise ExternalIdentityPreparationError("external_identity_subject_required")
        raw_aud = claims.get("aud", ())
        audience = (str(raw_aud),) if isinstance(raw_aud, str) else tuple(sorted({str(item) for item in raw_aud})) if isinstance(raw_aud, (list, tuple, set, frozenset)) else ()
        if self.expected_audience not in audience:
            raise ExternalIdentityPreparationError("external_identity_audience_denied")
        try:
            expires_at = float(claims.get("exp", 0.0))
        except (TypeError, ValueError) as exc:
            raise ExternalIdentityPreparationError("external_identity_expiry_invalid") from exc
        if expires_at <= float(self.clock()) - self.max_clock_skew_seconds:
            raise ExternalIdentityPreparationError("external_identity_expired")
        raw_scopes = claims.get("scope", claims.get("scopes", ()))
        scopes = tuple(sorted({str(item) for item in raw_scopes.split() if str(item)})) if isinstance(raw_scopes, str) else tuple(sorted({str(item) for item in raw_scopes})) if isinstance(raw_scopes, (list, tuple, set, frozenset)) else ()
        required = {str(item) for item in required_scopes}
        if not required.issubset(set(scopes)):
            raise ExternalIdentityPreparationError("external_identity_scope_denied")
        stable_claims = {"iss": issuer, "sub": subject, "aud": list(audience), "scope": list(scopes), "exp": expires_at}
        return PreparedExternalIdentity(issuer, subject, audience, scopes, expires_at, _digest(stable_claims))

    def readiness(self) -> Mapping[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "prepared_not_run",
            "trusted_issuer_count": len(self.trusted_issuers),
            "expected_audience": self.expected_audience,
            "external_verification": "NOT_RUN",
            "claim_boundary": "Decoded claims can be validated locally; provider token signature, key rotation, login, and network behavior require a pinned external adapter.",
        }


__all__ = ["SCHEMA_VERSION", "ExternalIdentityPreparationError", "PreparedExternalIdentity", "ExternalIdentityPreparation"]
