"""addons/webhook_sink.py

Optional, disabled-by-default outbound webhook sink for NOESIS agent memory
events. Pushes an event payload to an external HTTPS endpoint as a last step of
a fan-out, without ever blocking or raising inside the deterministic core.

BORROWED PATTERNS
-----------------
- LoopX: the "addon that degrades to a no-op when the optional backend is
  absent" pattern. LoopX ships its outbound notifier as a separate, soft
  dependency so the core never hard-requires `requests`. We mirror that: this
  module lives in addons/ (not noesis_harness/), imports `requests` lazily
  inside `send()`, and is DISABLED by default via the module flag `ENABLED`.

WHY LAZY + DISABLED-BY-DEFAULT
------------------------------
AGENTS.md rule 1 (zero dependencies) forbids third-party packages in the core.
`requests` is a heavy, optional transport. This module must therefore:
  * import cleanly even when `requests` is NOT installed, and
  * never raise on a missing dependency or on disablement — instead return a
    clear "disabled" dict (status == "disabled") so callers can branch without
    try/except.

The module flag `ENABLED = False` guarantees tests and default callers never
reach the network. `send` only performs a POST when BOTH `ENABLED` is true AND
`requests` is importable. Any transport error is caught and reported as a
status string; it never propagates.

HONESTY BOUNDARY
----------------
- When disabled or missing `requests`, `send` returns status "disabled" and does
  nothing. It never claims a delivery succeeded.
- When enabled but the POST fails, `send` returns status "error" with the reason;
  it never raises and never pretends the webhook fired.

Zero hard dependency on `requests` at import time. No module-level network I/O.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


ENABLED = False

DISABLED_STATUS = "disabled"


def _result(status: str, **fields: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": status}
    for key, val in fields.items():
        out[key] = val
    return out


def send(url: str, payload: Any, timeout: Optional[float] = 5.0) -> Dict[str, Any]:
    """POST `payload` to `url` as JSON if the sink is enabled and `requests` present.

    Returns a dict:
      - {"status": "disabled", "reason": ...} when ENABLED is False or `requests`
        cannot be imported (never raises, never touches the network).
      - {"status": "ok", "status_code": int, "url": str, "delivered": True} on a
        successful POST.
      - {"status": "error", "reason": ..., "delivered": False} if the POST raised.

    The sink is DISABLED by default. Tests must opt in by setting ENABLED=True
    AND mocking `requests`, or they will never perform network I/O.
    """
    if not ENABLED:
        return _result(
            DISABLED_STATUS,
            reason="webhook sink disabled (ENABLED=False)",
            delivered=False,
        )

    try:
        import requests  # type: ignore  # lazy: only inside send()
    except Exception as exc:  # ImportError or any lazy-load failure
        return _result(
            DISABLED_STATUS,
            reason="requests not installed: %s" % exc,
            delivered=False,
        )

    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        return _result(
            "ok",
            url=url,
            status_code=getattr(resp, "status_code", None),
            delivered=True,
        )
    except Exception as exc:  # network error, timeout, invalid URL, etc.
        return _result(
            "error",
            reason="%s" % exc,
            url=url,
            delivered=False,
        )
