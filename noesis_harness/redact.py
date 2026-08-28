"""noesis_harness/redact.py

Lightweight PII / secret redaction applied before durable writes.

Patterns adapted from:
  - LoopX        deterministic scrub-before-persist gate.
  - Hermes       telemetry redaction pass (secret-name driven).
  - agentmemory  privacy.ts redactor registry.

Stdlib only.
"""

from __future__ import annotations

import re

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"\+?\d[\d \-()]{8,}\d")
_SECRET = re.compile(r"(?i)(sk|pk|api|token|secret|bearer)[-_ ]?[A-Za-z0-9]{16,}")
_PASSWORD = re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+")


def redact(text):
    """Scrub emails, phones, token-shaped secrets and password assignments.

    Returns the original text when it is empty/None so callers can pass
    arbitrary fields through without special-casing.
    """
    if not text:
        return text
    out = _EMAIL.sub("[EMAIL]", text)
    out = _PHONE.sub("[PHONE]", out)
    out = _SECRET.sub("[SECRET]", out)
    out = _PASSWORD.sub(lambda m: m.group(1) + "=[REDACTED]", out)
    return out
