"""noesis_harness/metrics_collector.py

Numeric time-series metrics as a separate, machine-written layer.

Provenance (ported patterns):
    - AI-Builder-Club/skills, ``skills/new-loop/references/ARCHITECTURE.md``:
      "collectors write data, agents write knowledge; metrics are a separate
      numeric time-series written by deterministic collectors, not the LLM".

Design guarantees (AGENTS.md HARD rules):
    - Standard library only (``json``, ``math``, ``os``, ``re``, ``threading``).
    - Python 3.9 compatible syntax (``from __future__ import annotations``).
    - Append-only storage: one JSONL file per series, under
      ``root/<safe_series>.jsonl``. Existing lines are never rewritten or
      deleted.
    - Deterministic: identical call sequences produce byte-identical files and
      identical statistics; percentile ranking is the nearest-rank method.
    - Tolerant reads: malformed JSONL lines are skipped rather than raising.

The collector is the only writer. Agents read ``MetricPoint`` values from it;
they do not author raw metric lines.
"""

from __future__ import annotations

import json
import math
import os
import re
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_SAFE_SEGMENT_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_JSONL_SUFFIX = ".jsonl"


class MetricError(RuntimeError):
    """Raised for invalid metric values, series names, or unsupported input."""


def safe_series(name: str) -> str:
    """Return a safe filename segment for a series name.

    The name is stripped, non-safe runs collapse to ``-``, and path traversal
    (``..``, ``/``, ``\\``, ``os.sep``, ``os.altsep``) is rejected outright.
    Raises ``MetricError`` when the result would be empty or unsafe.
    """
    if not isinstance(name, str) or not name.strip():
        raise MetricError("metric_series_required")
    if ".." in name:
        raise MetricError("metric_series_unsafe")
    if "/" in name or "\\" in name or os.sep in name:
        raise MetricError("metric_series_unsafe")
    if os.altsep and os.altsep in name:
        raise MetricError("metric_series_unsafe")
    segment = _SAFE_SEGMENT_RE.sub("-", name.strip()).strip("-.")
    if not segment or segment in (".", ".."):
        raise MetricError("metric_series_empty")
    return segment


def _check_finite(value: float, label: str) -> float:
    """Coerce ``value`` to float and reject NaN/inf with ``MetricError``."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise MetricError("%s_not_a_number" % label)
    if math.isnan(number) or math.isinf(number):
        raise MetricError("%s_not_finite" % label)
    return number


def _percentile(sorted_values: List[float], percentile: float) -> Optional[float]:
    """Nearest-rank percentile over an already-sorted list.

    Rank is ``ceil(percentile / 100 * n)`` clamped to ``[1, n]``; the returned
    value is ``sorted_values[rank - 1]``. Returns ``None`` for an empty list.
    """
    if not sorted_values:
        return None
    n = len(sorted_values)
    rank = int(math.ceil(percentile / 100.0 * n))
    if rank < 1:
        rank = 1
    if rank > n:
        rank = n
    return sorted_values[rank - 1]


@dataclass(frozen=True)
class MetricPoint:
    """A single numeric observation in a named series."""

    series: str
    value: float
    at: float
    source: str = ""
    labels: Dict[str, str] = field(default_factory=dict)

    def to_json_line(self) -> str:
        """Serialize to a canonical (sorted-key) JSON line."""
        payload = {
            "series": self.series,
            "value": self.value,
            "at": self.at,
            "source": self.source,
            "labels": dict(self.labels),
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_json_line(cls, line: str) -> "MetricPoint":
        """Parse a JSONL line back into a ``MetricPoint``.

        Raises ``MetricError`` when the line is not a JSON object or is missing
        the required ``series``/``value``/``at`` fields.
        """
        try:
            payload = json.loads(line)
        except (ValueError, TypeError):
            raise MetricError("metric_line_invalid_json")
        if not isinstance(payload, dict):
            raise MetricError("metric_line_not_object")
        for key in ("series", "value", "at"):
            if key not in payload:
                raise MetricError("metric_line_missing_%s" % key)
        raw_labels = payload.get("labels") or {}
        if not isinstance(raw_labels, dict):
            raise MetricError("metric_line_labels_invalid")
        labels = {str(k): str(v) for k, v in raw_labels.items()}
        return cls(
            series=str(payload["series"]),
            value=float(payload["value"]),
            at=float(payload["at"]),
            source=str(payload.get("source", "")),
            labels=labels,
        )


@dataclass(frozen=True)
class MetricReport:
    """Aggregated summary of one series, ready for rendering."""

    series: str
    count: int
    mean: Optional[float]
    p50: Optional[float]
    p95: Optional[float]
    latest: Optional[float]

    def as_dict(self) -> Dict:
        """Return a plain-dict representation with stable key names."""
        return {
            "series": self.series,
            "count": self.count,
            "mean": self.mean,
            "p50": self.p50,
            "p95": self.p95,
            "latest": self.latest,
        }


class MetricCollector:
    """Append-only, per-series numeric time-series store rooted at ``root``.

    One JSONL file is written per series at ``root/<safe_series>.jsonl``. Files
    are created lazily on first ``emit`` and are never deleted. Reads are
    tolerant: malformed lines are skipped.
    """

    def __init__(self, root: str, source: str = "collector") -> None:
        if not isinstance(root, str) or not root.strip():
            raise MetricError("metric_root_required")
        self.root = os.path.abspath(os.path.expanduser(root))
        self.source = str(source)
        self._lock = threading.Lock()

    # -- paths -------------------------------------------------------------

    def series_path(self, series: str) -> str:
        """Return the absolute JSONL path for ``series`` (does not create it)."""
        return os.path.join(self.root, safe_series(series) + _JSONL_SUFFIX)

    # -- writes ------------------------------------------------------------

    def emit(
        self,
        series: str,
        value: float,
        at: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> str:
        """Append one point to ``series`` and return the JSONL file path.

        ``value`` must be a finite float; NaN/inf raise ``MetricError``. The
        point is durably appended immediately, so ``flush`` is a no-op kept for
        API symmetry.
        """
        path = self.series_path(series)
        number = _check_finite(value, "metric_value")
        stamp = _check_finite(at, "metric_at")
        label_map = {str(k): str(v) for k, v in (labels or {}).items()}
        point = MetricPoint(
            series=str(series),
            value=number,
            at=stamp,
            source=self.source,
            labels=label_map,
        )
        line = point.to_json_line()
        os.makedirs(self.root, exist_ok=True)
        with self._lock:
            with open(path, "a", encoding="utf-8", newline="\n") as handle:
                handle.write(line + "\n")
        return path

    def flush(self) -> None:
        """No-op. ``emit`` already writes durably; kept for API symmetry."""
        return None

    # -- reads -------------------------------------------------------------

    def series_points(self, series: str) -> List[MetricPoint]:
        """Return all valid points for ``series`` in file order.

        Malformed lines are skipped tolerantly. A missing file yields ``[]``.
        """
        path = self.series_path(series)
        if not os.path.exists(path):
            return []
        points: List[MetricPoint] = []
        with open(path, "r", encoding="utf-8", newline="") as handle:
            for raw in handle:
                line = raw.strip()
                if not line:
                    continue
                try:
                    points.append(MetricPoint.from_json_line(line))
                except MetricError:
                    continue
        return points

    def series_names(self) -> List[str]:
        """Return the sorted base names of all series files under ``root``."""
        if not os.path.isdir(self.root):
            return []
        names: List[str] = []
        for name in os.listdir(self.root):
            if not name.endswith(_JSONL_SUFFIX):
                continue
            if not os.path.isfile(os.path.join(self.root, name)):
                continue
            names.append(name[: -len(_JSONL_SUFFIX)])
        return sorted(names)

    def latest(self, series: str) -> Optional[MetricPoint]:
        """Return the last valid point for ``series`` or ``None``."""
        points = self.series_points(series)
        return points[-1] if points else None

    def mean(self, series: str) -> Optional[float]:
        """Return the arithmetic mean of the series or ``None`` when empty."""
        values = [point.value for point in self.series_points(series)]
        if not values:
            return None
        return sum(values) / float(len(values))

    def p50(self, series: str) -> Optional[float]:
        """Return the nearest-rank 50th percentile or ``None`` when empty."""
        values = sorted(point.value for point in self.series_points(series))
        return _percentile(values, 50.0)

    def p95(self, series: str) -> Optional[float]:
        """Return the nearest-rank 95th percentile or ``None`` when empty."""
        values = sorted(point.value for point in self.series_points(series))
        return _percentile(values, 95.0)

    def window(self, series: str, since: float, until: float) -> List[MetricPoint]:
        """Return points with ``since <= at <= until`` in file order."""
        return [
            point
            for point in self.series_points(series)
            if since <= point.at <= until
        ]

    def stats(self) -> Dict:
        """Return per-series point counts plus the total point count."""
        counts: Dict[str, int] = {}
        total = 0
        for name in self.series_names():
            count = len(self.series_points(name))
            counts[name] = count
            total += count
        return {
            "series": counts,
            "series_count": len(counts),
            "total_points": total,
        }


def build_report(collector: MetricCollector, series: str) -> MetricReport:
    """Build a ``MetricReport`` for ``series`` from a collector."""
    points = collector.series_points(series)
    latest_point = points[-1] if points else None
    return MetricReport(
        series=str(series),
        count=len(points),
        mean=collector.mean(series),
        p50=collector.p50(series),
        p95=collector.p95(series),
        latest=latest_point.value if latest_point is not None else None,
    )


__all__ = [
    "MetricError",
    "MetricPoint",
    "MetricCollector",
    "MetricReport",
    "build_report",
    "safe_series",
]
