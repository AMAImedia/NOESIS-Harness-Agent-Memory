"""noesis_harness/privacy.py

Regex privacy filter applied before memory writes.

Pattern adapted from agentmemory privacy.ts: a registry of redactors so
secrets never land in the durable store.

Stdlib only.
"""

from __future__ import annotations

import re


class PrivacyFilter:
    """Scrub emails, phones, tokens, and custom patterns from text."""

    DEFAULTS = (
        (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
        (re.compile(r"\+?\d[\d \-()]{8,}\d"), "[PHONE]"),
        (re.compile(r"(?i)(sk|pk|api|token|secret|bearer)[-_ ]?[A-Za-z0-9]{16,}"), "[SECRET]"),
        (re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+"), r"\1=[REDACTED]"),
    )

    def __init__(self, extra=None):
        self.rules = list(self.DEFAULTS)
        if extra:
            for pat, repl in extra:
                self.rules.append((re.compile(pat) if isinstance(pat, str) else pat, repl))

    def scrub(self, text):
        if not text:
            return text
        out = text
        for pat, repl in self.rules:
            out = pat.sub(repl, out)
        return out
