"""Verifiable evidence-corpus bindings for governed learning proposals.

Gate 1: review proposals must carry evidence-corpus provenance that can be
verified independently. A binding is a tamper-evident, deterministic envelope
that pins a promotion proposal to an evaluate_corpus_v2 report digest.

Pattern lineage: integrity-digest envelope and fail-closed verification follow
the agentmemory governance audit pattern as already ported in
learning_promotion/promotion_integration (canonical JSON + sha256 +
hmac.compare_digest), and the fail-closed provenance discipline of
deepseek-harness adversarial suites mirrored in
memory_quality_corpora.verify_case_provenance. Deterministic core rule holds:
no wall clock is read unless the caller injects one; bindings without an
injected clock are byte-stable across runs and machines.
"""
from __future__ import annotations

from dataclasses import asdict
import hmac
import json
import math
import re
from collections.abc import MutableMapping
from typing import Any, Callable, Mapping, Optional

from .memory_quality_corpora import CORPUS_SCHEMA_VERSION


BINDING_SCHEMA_VERSION = "noesis.learning-corpus-binding.v1"
TELEMETRY_BINDING_KEY = "corpus_binding"

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_DIGEST_HEX = re.compile(r"^sha256:[0-9a-f]{64}$")
_SUBJECT_KIND = "promotion_proposal"

_ALLOWED_KEYS = frozenset({
    "schema_version",
    "corpus_schema_version",
    "corpus_report_digest",
    "subject",
    "bound_at_unix",
    "max_age_seconds",
    "binding_digest",
})
_REQUIRED_KEYS = _ALLOWED_KEYS - {"bound_at_unix", "max_age_seconds"}
_SUBJECT_KEYS = frozenset({"kind", "proposal_id", "skill_digest", "provenance_digest"})


class LearningCorpusBindingError(ValueError):
    """Raised when a corpus binding cannot be built or attached safely."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    import hashlib

    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _safe_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_SAFE_ID.fullmatch(value))


def _digest_shape(value: Any) -> bool:
    return isinstance(value, str) and bool(_DIGEST_HEX.fullmatch(value))


def _is_positive_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    number = float(value)
    return math.isfinite(number) and number > 0.0


def _validated_report(corpus_report: Any) -> dict:
    if not isinstance(corpus_report, Mapping):
        raise LearningCorpusBindingError("corpus_report_invalid")
    schema = corpus_report.get("schema_version")
    report_digest = corpus_report.get("report_digest")
    if schema != CORPUS_SCHEMA_VERSION or not _digest_shape(report_digest):
        raise LearningCorpusBindingError("corpus_report_invalid")
    return {"schema_version": str(schema), "report_digest": str(report_digest)}


def _subject_fields(subject: Any) -> dict:
    """Normalize a PromotionProposal, proposal-like mapping, or zero-arg builder."""
    if callable(subject) and not isinstance(subject, Mapping):
        try:
            subject = subject()
        except Exception as exc:
            raise LearningCorpusBindingError("subject_builder_failed") from exc
    if hasattr(subject, "__dataclass_fields__"):
        candidate = asdict(subject)
    elif isinstance(subject, Mapping):
        candidate = dict(subject)
    else:
        raise LearningCorpusBindingError("subject_invalid")
    proposal_id = candidate.get("proposal_id")
    if not _safe_id(proposal_id):
        raise LearningCorpusBindingError("subject_proposal_id_invalid")
    skill_digest = candidate.get("content_digest")
    provenance_digest = candidate.get("provenance_digest")
    for value in (skill_digest, provenance_digest):
        if not isinstance(value, str) or len(value) > 256:
            raise LearningCorpusBindingError("subject_digests_invalid")
    # Key names are deliberately redaction-safe: PromotionTelemetry._redact
    # masks any key containing "content", so the canonical PromotionProposal
    # field ``content_digest`` is recorded here under ``skill_digest`` to keep
    # the binding verifiable on operator telemetry surfaces.
    return {
        "kind": _SUBJECT_KIND,
        "proposal_id": str(proposal_id),
        "skill_digest": skill_digest,
        "provenance_digest": provenance_digest,
    }


def bind_corpus_evidence(
    proposal_builder_or_proposal: Any,
    corpus_report: Mapping[str, Any],
    *,
    max_age_seconds: Optional[float] = None,
    clock: Optional[Callable[[], float]] = None,
) -> dict:
    """Bind a promotion proposal to an evidence-corpus report.

    Accepts a ``PromotionProposal``, a proposal-like mapping, or a zero-arg
    callable returning either. The returned dict carries ``schema_version``,
    ``corpus_schema_version``, ``corpus_report_digest``, the normalized
    ``subject``, an optional ``bound_at_unix`` (present only when ``clock``
    is injected; the default output stays deterministic with no timestamp),
    an optional ``max_age_seconds`` freshness policy (requires ``clock``),
    and a ``binding_digest`` integrity digest over the canonical binding.
    """
    report = _validated_report(corpus_report)
    core = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "corpus_schema_version": report["schema_version"],
        "corpus_report_digest": report["report_digest"],
        "subject": _subject_fields(proposal_builder_or_proposal),
    }
    if clock is not None:
        if not callable(clock):
            raise LearningCorpusBindingError("clock_not_callable")
        bound_at = float(clock())
        if not math.isfinite(bound_at) or bound_at < 0.0:
            raise LearningCorpusBindingError("clock_value_invalid")
        core["bound_at_unix"] = bound_at
    if max_age_seconds is not None:
        if not _is_positive_number(max_age_seconds):
            raise LearningCorpusBindingError("max_age_seconds_invalid")
        if "bound_at_unix" not in core:
            raise LearningCorpusBindingError("clock_required_for_max_age")
        core["max_age_seconds"] = float(max_age_seconds)
    core["binding_digest"] = _digest(core)
    return core


def verify_corpus_binding(binding: Any, *, corpus_report: Optional[Mapping[str, Any]] = None) -> bool:
    """Fail-closed check: tampered digest, malformed shape, or a mismatched
    corpus report all return False (never raises)."""
    try:
        if not isinstance(binding, Mapping):
            return False
        keys = set(binding)
        if not _REQUIRED_KEYS.issubset(keys) or not keys.issubset(_ALLOWED_KEYS):
            return False
        if binding.get("schema_version") != BINDING_SCHEMA_VERSION:
            return False
        if binding.get("corpus_schema_version") != CORPUS_SCHEMA_VERSION:
            return False
        if not _digest_shape(binding.get("corpus_report_digest")):
            return False
        subject = binding.get("subject")
        if not isinstance(subject, Mapping) or set(subject) != set(_SUBJECT_KEYS):
            return False
        if subject.get("kind") != _SUBJECT_KIND:
            return False
        if not _safe_id(subject.get("proposal_id")):
            return False
        for key in ("skill_digest", "provenance_digest"):
            value = subject.get(key)
            if not isinstance(value, str) or len(value) > 256:
                return False
        supplied = binding.get("binding_digest")
        unsigned = {key: value for key, value in binding.items() if key != "binding_digest"}
        if not isinstance(supplied, str) or not hmac.compare_digest(supplied, _digest(unsigned)):
            return False
        if "bound_at_unix" in binding and not _is_positive_number(binding["bound_at_unix"]):
            return False
        if "max_age_seconds" in binding:
            if "bound_at_unix" not in binding or not _is_positive_number(binding["max_age_seconds"]):
                return False
        if corpus_report is not None:
            report = _validated_report(corpus_report)
            if binding["corpus_schema_version"] != report["schema_version"]:
                return False
            if not hmac.compare_digest(str(binding["corpus_report_digest"]), report["report_digest"]):
                return False
        return True
    except LearningCorpusBindingError:
        return False


def attach_to_telemetry(telemetry_payload: MutableMapping, binding: Any) -> MutableMapping:
    """Attach a verified binding under ``corpus_binding``; never overwrite.

    Idempotency conflict policy is fail-closed: an existing key raises
    instead of being silently replaced.
    """
    if not isinstance(telemetry_payload, MutableMapping):
        raise LearningCorpusBindingError("telemetry_payload_invalid")
    if TELEMETRY_BINDING_KEY in telemetry_payload:
        raise LearningCorpusBindingError("telemetry_binding_conflict")
    if not verify_corpus_binding(binding):
        raise LearningCorpusBindingError("binding_verification_failed")
    telemetry_payload[TELEMETRY_BINDING_KEY] = dict(binding)
    return telemetry_payload


__all__ = [
    "BINDING_SCHEMA_VERSION",
    "LearningCorpusBindingError",
    "TELEMETRY_BINDING_KEY",
    "attach_to_telemetry",
    "bind_corpus_evidence",
    "verify_corpus_binding",
]
