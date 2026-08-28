"""Safe-logging sanitizer for the NOESIS harness agent memory.

Borrows the "no secrets in logs" pattern from LoopX, which strips control
characters and caps length before any value is written to a log line so that
accidental `repr()` of objects never leaks credentials or oversized blobs.

This module is pure: it has no side effects, calls no LLM, and depends only on
the Python standard library.
"""

import math

_MAX_LEN = 1024
_ELLIPSIS = "..."


def sanitize(value, max_len=_MAX_LEN):
    """Convert any object to a safe string for logging.

    Control characters (including newlines, tabs, and other non-printable
    codepoints below 0x20 and the DEL codepoint 0x7f) are stripped. The result
    is capped at ``max_len`` characters; over-long values are truncated and
    suffixed with an ellipsis so logs stay bounded and no secret hides in a
    giant repr. Objects are stringified with ``str()`` only -- ``repr()`` is
    never used, so object internals are not leaked.

    Args:
        value: Any Python object.
        max_len: Maximum number of characters in the returned string.

    Returns:
        str: A sanitized, bounded, control-char-free string.
    """
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    elif isinstance(value, (bytes, bytearray)):
        try:
            text = value.decode("utf-8", errors="replace")
        except Exception:
            text = str(value)
    elif isinstance(value, (dict, list, tuple, set, frozenset)):
        text = str(value)
    else:
        # Unknown objects are reduced to a generic tag rather than str()/repr(),
        # so their type name, attributes, ids, and secrets can never leak.
        text = "<object>"

    cleaned = "".join(
        ch for ch in text
        if ch == " " or ord(ch) >= 0x20 and ord(ch) != 0x7f
    )

    if max_len is None or max_len < 0:
        return cleaned
    if len(cleaned) > max_len:
        return cleaned[:max_len] + _ELLIPSIS
    return cleaned
