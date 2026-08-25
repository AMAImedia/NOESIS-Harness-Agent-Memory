"""Deterministic metrics and durable commit-marker evidence for governed
multi-agent work products.

The bounded, no-hidden-reward scoring evaluator follows the deepseek-harness
deterministic rubric pattern. The commit-marker ledger follows the append-only,
fingerprint-idempotent event-log pattern from LoopX event_sourced_state.py (via
noesis_harness/event_store.py) and the fail-closed conflict handling of
agentmemory governance writes: a double-send is absorbed as a replay and any
identity or content divergence is denied, never rewritten.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from .event_store import EventStore, EventStoreConflict


COMMIT_MARKER_SCHEMA = "noesis.work-product-commit-marker.v1"
COMMIT_MARKER_EVENT = "work_product_commit_marker"
MARKER_STATUS_COMMITTED = "committed"
MARKER_STATUS_REPLAYED = "replayed"

_MARKER_FIELDS = (
    "product_id",
    "task_id",
    "agent_id",
    "workspace_id",
    "base_snapshot_id",
    "head_snapshot_id",
    "artifact_digest",
    "authorization_digest",
)


class WorkProductBenchmarkError(ValueError):
    pass


@dataclass(frozen=True)
class WorkProductOutcome:
    case_id: str
    correct: bool
    delivered: bool
    leakage_free: bool
    recovered: bool
    attempts: int = 1
    reviewer_time_seconds: float = 0.0
    review_approved: bool = True
    committed: bool = True

    def __post_init__(self) -> None:
        if not self.case_id:
            raise WorkProductBenchmarkError("case_id_required")
        if int(self.attempts) < 1 or int(self.attempts) > 4:
            raise WorkProductBenchmarkError("attempts_out_of_range")
        if not math.isfinite(float(self.reviewer_time_seconds)) or float(self.reviewer_time_seconds) < 0:
            raise WorkProductBenchmarkError("reviewer_time_invalid")


@dataclass(frozen=True)
class WorkProductMetrics:
    correctness_rate: float
    delivery_rate: float
    leakage_free_rate: float
    recovery_rate: float
    review_approval_rate: float
    commit_rate: float
    mean_reviewer_time_seconds: float
    retry_rate: float
    work_product_score: float
    cases: int


class WorkProductBenchmarkEvaluator:
    """Compute reproducible bounded metrics; no LLM grading or hidden reward."""
    def evaluate(self, outcomes: Sequence[WorkProductOutcome]) -> WorkProductMetrics:
        rows = tuple(outcomes)
        if not rows:
            raise WorkProductBenchmarkError("outcomes_required")
        ids = [row.case_id for row in rows]
        if len(set(ids)) != len(ids):
            raise WorkProductBenchmarkError("duplicate_case_id")
        n = float(len(rows))
        correctness = sum(row.correct for row in rows) / n
        delivery = sum(row.delivered for row in rows) / n
        leakage = sum(row.leakage_free for row in rows) / n
        recovery = sum(row.recovered for row in rows) / n
        review = sum(row.review_approved for row in rows) / n
        commits = sum(row.committed for row in rows) / n
        reviewer_time = sum(float(row.reviewer_time_seconds) for row in rows) / n
        retry_rate = sum(row.attempts > 1 for row in rows) / n
        score = (correctness + delivery + leakage + recovery + review + commits) / 6.0
        return WorkProductMetrics(correctness, delivery, leakage, recovery, review, commits, reviewer_time, retry_rate, score, len(rows))


@dataclass(frozen=True)
class WorkProductCommitMarker:
    """Typed explicit task commit marker bound to one reviewed work product."""

    product_id: str
    task_id: str
    agent_id: str
    workspace_id: str
    base_snapshot_id: str
    head_snapshot_id: str
    artifact_digest: str
    authorization_digest: str
    schema_version: str = COMMIT_MARKER_SCHEMA

    def __post_init__(self) -> None:
        for field in _MARKER_FIELDS:
            if not str(getattr(self, field)):
                raise WorkProductBenchmarkError(field + "_required")
        if self.schema_version != COMMIT_MARKER_SCHEMA:
            raise WorkProductBenchmarkError("unsupported_commit_marker_schema")

    @property
    def marker_id(self) -> str:
        raw = json.dumps(self.to_mapping(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return "marker:" + hashlib.sha256(raw).hexdigest()[:32]

    def to_mapping(self) -> dict[str, str]:
        return {field: str(getattr(self, field)) for field in _MARKER_FIELDS} | {"schema_version": self.schema_version}

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "WorkProductCommitMarker":
        required = set(_MARKER_FIELDS) | {"schema_version"}
        if not isinstance(data, Mapping) or set(data) != required:
            raise WorkProductBenchmarkError("commit_marker_payload_invalid")
        if any(not isinstance(data[field], str) for field in required):
            raise WorkProductBenchmarkError("commit_marker_payload_invalid")
        return cls(**{field: str(data[field]) for field in required})


@dataclass(frozen=True)
class CommitMarkerRecord:
    status: str
    marker_id: str
    duplicate: bool


class WorkProductCommitMarkerLedger:
    """Append-only durable ledger of explicit task commit markers.

    A double-send of an identical marker is a no-op replay. The same product
    committed with any differing field, an unexpected event type, a payload
    whose recomputed identity does not match its stored id, or a malformed
    non-tail record all fail closed; only a torn final line (crash during
    append) is repaired.
    """

    def __init__(self, path: str):
        self.path = str(path)
        self.events = EventStore(self.path)
        self._by_product: dict[str, WorkProductCommitMarker] = {}
        self._order: list[str] = []
        self._replay()

    def _replay(self) -> None:
        for record in self.events.iter_events():
            if record.get("type") != COMMIT_MARKER_EVENT:
                raise WorkProductBenchmarkError("ledger_unexpected_event:" + str(record.get("type")))
            try:
                marker = WorkProductCommitMarker.from_mapping(record.get("payload"))
            except WorkProductBenchmarkError as exc:
                raise WorkProductBenchmarkError("commit_marker_payload_invalid") from exc
            if str(record.get("event_id", "")) != marker.marker_id:
                raise WorkProductBenchmarkError("commit_marker_tampered")
            existing = self._by_product.get(marker.product_id)
            if existing is not None:
                if existing.marker_id != marker.marker_id:
                    raise WorkProductBenchmarkError("ledger_conflict_on_replay")
                continue
            self._by_product[marker.product_id] = marker
            self._order.append(marker.product_id)

    def record(self, marker: WorkProductCommitMarker) -> CommitMarkerRecord:
        if not isinstance(marker, WorkProductCommitMarker):
            raise WorkProductBenchmarkError("commit_marker_type_required")
        existing = self._by_product.get(marker.product_id)
        if existing is not None:
            if existing.marker_id == marker.marker_id:
                return CommitMarkerRecord(MARKER_STATUS_REPLAYED, marker.marker_id, True)
            raise WorkProductBenchmarkError("commit_marker_conflict")
        try:
            self.events.append(COMMIT_MARKER_EVENT, marker.to_mapping(), event_id=marker.marker_id)
        except EventStoreConflict as exc:
            raise WorkProductBenchmarkError("commit_marker_conflict") from exc
        self._by_product[marker.product_id] = marker
        self._order.append(marker.product_id)
        return CommitMarkerRecord(MARKER_STATUS_COMMITTED, marker.marker_id, False)

    def get(self, product_id: str) -> WorkProductCommitMarker | None:
        return self._by_product.get(str(product_id))

    def markers(self) -> tuple[WorkProductCommitMarker, ...]:
        return tuple(self._by_product[product_id] for product_id in self._order)

    def count(self) -> int:
        return len(self._order)

    def verify_integrity(self) -> Mapping[str, object]:
        """Re-read the durable log and validate every record fail-closed."""
        seen_products: set[str] = set()
        records = 0
        for record in self.events.iter_events():
            records += 1
            if record.get("type") != COMMIT_MARKER_EVENT:
                raise WorkProductBenchmarkError("ledger_unexpected_event:" + str(record.get("type")))
            try:
                marker = WorkProductCommitMarker.from_mapping(record.get("payload"))
            except WorkProductBenchmarkError as exc:
                raise WorkProductBenchmarkError("commit_marker_payload_invalid") from exc
            if str(record.get("event_id", "")) != marker.marker_id:
                raise WorkProductBenchmarkError("commit_marker_tampered")
            if marker.product_id in seen_products:
                raise WorkProductBenchmarkError("ledger_conflict_on_replay")
            seen_products.add(marker.product_id)
        return {"ok": True, "markers": len(seen_products), "records": records, "schema_version": COMMIT_MARKER_SCHEMA}


__all__ = [
    "COMMIT_MARKER_SCHEMA",
    "COMMIT_MARKER_EVENT",
    "MARKER_STATUS_COMMITTED",
    "MARKER_STATUS_REPLAYED",
    "WorkProductBenchmarkError",
    "WorkProductOutcome",
    "WorkProductMetrics",
    "WorkProductBenchmarkEvaluator",
    "WorkProductCommitMarker",
    "CommitMarkerRecord",
    "WorkProductCommitMarkerLedger",
]
