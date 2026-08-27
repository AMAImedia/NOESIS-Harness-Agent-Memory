"""addons/otel_adapter.py

Optional, disabled-by-default adapter that emits OpenTelemetry metrics and
spans from NOESIS agent memory events.

BORROWED PATTERNS
-----------------
- LoopX: the "addon that degrades to a no-op when the optional backend is
  absent" pattern. LoopX ships instrumentation as a separate, soft dependency
  so the core never hard-requires an exporter. We mirror that: this module is
  in addons/ (not noesis_harness/) and only touches opentelemetry lazily,
  inside the functions that need it.

WHY LAZY + DISABLED-BY-DEFAULT
------------------------------
AGENTS.md rule 1 (zero dependencies) forbids third-party packages in the core.
OpenTelemetry is a heavy, optional observability backend. This module must
therefore:
  * import cleanly even when `opentelemetry` is NOT installed, and
  * never raise on missing dependencies — instead return a clear "disabled"
    dict (status == "disabled") so callers can branch without try/except.

Every public function guards on lazy import failure and returns the disabled
shape. There is no global state that imports opentelemetry at module load.

HONESTY BOUNDARY
----------------
- If opentelemetry is missing, `emit` and `span` report status "disabled" and
  do nothing. They never claim a metric was recorded or a span was exported.
- `span` returns a context-manager-like object that is a safe no-op in disabled
  mode, so callers can `with span("x"):` unconditionally.

Zero hard dependency on opentelemetry at import time.
"""

from __future__ import annotations

import contextlib
from typing import Any, Dict, Iterator, Optional


def _disabled_result(reason: str) -> Dict[str, Any]:
    return {
        "status": "disabled",
        "reason": reason,
        "recorded": False,
    }


def emit(metric_name: str, value: float, attrs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Emit a numeric metric to OpenTelemetry if available.

    Returns a dict with status "ok" when the metric was recorded, or status
    "disabled" (recorded False) when opentelemetry is not installed. Never
    raises on a missing backend.
    """
    try:
        from opentelemetry import metrics  # type: ignore
        from opentelemetry.metrics import Counter, Meter  # type: ignore
    except Exception as exc:  # ImportError or any lazy-load failure
        return _disabled_result("opentelemetry not installed: %s" % exc)

    meter = metrics.get_meter("noesis_harness")
    counter = meter.create_counter(metric_name)
    counter.add(float(value), attributes=attrs or {})
    return {
        "status": "ok",
        "metric": metric_name,
        "value": float(value),
        "attributes": attrs or {},
        "recorded": True,
    }


@contextlib.contextmanager
def span(name: str, attrs: Optional[Dict[str, Any]] = None) -> Iterator[Dict[str, Any]]:
    """Context manager that wraps a block in an OpenTelemetry span.

    In disabled mode (opentelemetry missing) this is a no-op: the block runs
    normally, and the yielded dict carries status "disabled". Never raises on a
    missing backend.
    """
    try:
        from opentelemetry import trace  # type: ignore
    except Exception as exc:  # ImportError or any lazy-load failure
        yield _disabled_result("opentelemetry not installed: %s" % exc)
        return

    tracer = trace.get_tracer("noesis_harness")
    with tracer.start_as_current_span(name) as sp:
        for key, val in (attrs or {}).items():
            sp.set_attribute(key, val)
        yield {
            "status": "ok",
            "span": name,
            "attributes": attrs or {},
            "recorded": True,
        }
