"""Tolerant, dependency-free frontmatter parsing and YAML-safe emission.

Provenance: ported from the ``wshobson/agents`` repository
(``tools/adapters/base.py``), which hand-rolls a small frontmatter parser and
a quote-safe scalar emitter in order to avoid a PyYAML dependency. This
module keeps the same spirit: it reads the ``key: value`` header block used
by skill/agent manifests, tolerates malformed input, and defends against
YAML 1.1 ambiguity (yes/no/on/off, numeric-looking strings, special
characters) on both the parse and the emit side.

Only the Python standard library is used (``re``, ``typing``). The module is
pure and deterministic: no I/O, no global state. Parsing never raises for
ordinary malformed input; it degrades to "no frontmatter" instead.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "FrontmatterError",
    "parse_frontmatter",
    "yaml_scalar",
    "render_frontmatter",
    "roundtrip",
]


class FrontmatterError(ValueError):
    """Raised for invalid *types* passed to the frontmatter helpers.

    Ordinary malformed text is tolerated rather than reported, so this error
    is reserved for programming mistakes such as passing ``None`` or a bytes
    object where ``str`` is required.
    """


_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?$")

_RESERVED_WORDS = frozenset(
    {
        "true",
        "false",
        "yes",
        "no",
        "on",
        "off",
        "null",
        "~",
        "none",
    }
)

_SPECIAL_CHARS = set(":#{}[],&*!|>'\"%@`")


def _strip_comment(raw: str) -> str:
    """Remove an unquoted ``#`` comment from a raw value string.

    Quote state is tracked so ``"a # b"`` keeps its hash. Backslash escapes are
    honoured only inside double quotes, matching the parser's unquoting rules.
    """
    out: List[str] = []
    quote: Optional[str] = None
    escaped = False
    for ch in raw:
        if escaped:
            out.append(ch)
            escaped = False
            continue
        if quote == '"' and ch == "\\":
            out.append(ch)
            escaped = True
            continue
        if quote is not None:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            out.append(ch)
            continue
        if ch == "#":
            break
        out.append(ch)
    return "".join(out)


def _unquote(value: str) -> str:
    """Strip one layer of matching surrounding quotes if present."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        quote = value[0]
        inner = value[1:-1]
        if quote == '"':
            inner = inner.replace('\\"', '"')
            inner = inner.replace('""', '"')
        else:
            inner = inner.replace("''", "'")
        return inner
    return value


def _split_quoted(text: str) -> List[str]:
    """Split ``text`` on commas that are outside quotes."""
    parts: List[str] = []
    buf: List[str] = []
    quote: Optional[str] = None
    escaped = False
    for ch in text:
        if escaped:
            buf.append(ch)
            escaped = False
            continue
        if quote == '"' and ch == "\\":
            buf.append(ch)
            escaped = True
            continue
        if quote is not None:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            buf.append(ch)
            continue
        if ch == ",":
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    parts.append("".join(buf))
    return parts


def _parse_inline_list(value: str) -> List[str]:
    """Parse a ``[a, b, c]`` inline list into a list of stripped strings."""
    inner = value[1:-1].strip()
    if inner == "":
        return []
    items: List[str] = []
    for part in _split_quoted(inner):
        part = part.strip()
        if part == "":
            continue
        items.append(_unquote(part).strip())
    return items


def _coerce_scalar(value: str) -> Any:
    """Apply the tolerant YAML-ish scalar rules to a cleaned value string."""
    if value == "":
        return ""
    if value.startswith("[") and value.endswith("]"):
        return _parse_inline_list(value)
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in ("null", "~", "none"):
        return None
    if _INT_RE.match(value):
        try:
            return int(value)
        except ValueError:  # pragma: no cover - defensive
            return value
    if _FLOAT_RE.match(value):
        try:
            return float(value)
        except ValueError:  # pragma: no cover - defensive
            return value
    return _unquote(value)


def _parse_header_line(line: str, fields: Dict[str, Any]) -> None:
    """Parse one header line into ``fields``; ignore lines without a colon."""
    if ":" not in line:
        return
    key, _, raw_value = line.partition(":")
    key = key.strip()
    if key == "":
        return
    cleaned = _strip_comment(raw_value).strip()
    fields[key] = _coerce_scalar(cleaned)


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Split a document into its frontmatter fields and body.

    A document optionally starts with a line containing only ``---`` followed
    by ``key: value`` lines and an optional closing ``---`` line. If there is
    no leading ``---`` the original ``text`` is returned unchanged alongside
    an empty mapping.

    Scalar rules: empty becomes ``""``; ``[...]`` becomes ``List[str]``;
    ``true``/``false`` (any case) become ``bool``; ``null``/``~``/``none``
    (any case) become ``None``; integer and float literals are converted;
    everything else stays a string with one layer of matching quotes removed.
    Unquoted ``#`` comments are stripped. Lines without a colon inside the
    header are ignored.

    The closing delimiter is optional. When it is missing the header block
    runs until the first blank line or the first line without a colon. The
    returned body has leading newlines removed.

    Raises ``FrontmatterError`` only when ``text`` is not a ``str``.
    """
    if not isinstance(text, str):
        raise FrontmatterError(
            "parse_frontmatter expects str, got %s" % type(text).__name__
        )

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    if not lines:
        return {}, text

    first = lines[0].lstrip("\ufeff").strip()
    if first != "---":
        return {}, text

    closing_index: Optional[int] = None
    probe = 1
    while probe < len(lines):
        stripped = lines[probe].strip()
        if stripped == "---":
            closing_index = probe
            break
        if stripped == "":
            break
        probe += 1

    fields: Dict[str, Any] = {}
    if closing_index is not None:
        for index in range(1, closing_index):
            _parse_header_line(lines[index].strip(), fields)
        body_start = closing_index + 1
    else:
        body_start = len(lines)
        index = 1
        while index < len(lines):
            stripped = lines[index].strip()
            if stripped == "" or ":" not in stripped:
                body_start = index
                break
            _parse_header_line(stripped, fields)
            index += 1

    body = "\n".join(lines[body_start:]).lstrip("\n")
    return fields, body


def _looks_numeric(text: str) -> bool:
    """Return True when ``text`` would parse back as an int or float."""
    return bool(_INT_RE.match(text) or _FLOAT_RE.match(text))


def _needs_quotes(text: str) -> bool:
    """Return True when ``text`` must be quoted to stay unambiguous."""
    if text == "":
        return True
    if text != text.strip():
        return True
    if "\n" in text or "\r" in text:
        return True
    for ch in text:
        if ch in _SPECIAL_CHARS:
            return True
    if text.lower() in _RESERVED_WORDS:
        return True
    if _looks_numeric(text):
        return True
    return False


def _emit_string(text: str) -> str:
    """Emit a string scalar, double-quoting and doubling quotes if needed."""
    if _needs_quotes(text):
        return '"' + text.replace('"', '""') + '"'
    return text


def yaml_scalar(value: Any) -> str:
    """Emit a YAML-safe scalar string for ``value``.

    ``None`` becomes ``null`` and booleans become ``true``/``false``. Numbers
    are emitted as-is. Lists and tuples become inline ``[a, b]`` sequences.
    Strings stay unquoted when safe; they are double-quoted with inner quotes
    doubled when empty, padded with space, or containing a newline or any of
    ``:#{}[],&*!|>'\"%@`` `` ` `` or when they would otherwise be ambiguous
    (a YAML 1.1 reserved word such as ``yes``/``off``/``null``, or a
    numeric-looking string).
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(yaml_scalar(item) for item in value) + "]"
    if isinstance(value, str):
        return _emit_string(value)
    return _emit_string(str(value))


def render_frontmatter(fields: Dict[str, Any], body: str = "") -> str:
    """Render ``fields`` and ``body`` as a frontmatter document.

    The output is ``---\\nkey: scalar\\n---\\n\\nbody``. Plain ``dict`` input
    has its keys sorted for deterministic output. A mapping subclass such as
    ``collections.OrderedDict`` is emitted in the order given, since it
    carries an explicit ordering. Note that plain ``dict`` preserves insertion
    order on Python 3.7+, so callers who want insertion order should pass an
    ordered mapping subclass.
    """
    if body is None:
        body = ""
    items = list(fields.items())
    if type(fields) is dict:
        items.sort(key=lambda pair: pair[0])
    lines = ["---"]
    for key, value in items:
        lines.append("%s: %s" % (key, yaml_scalar(value)))
    lines.append("---")
    header = "\n".join(lines) + "\n"
    return header + "\n" + body.lstrip("\n")


def roundtrip(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Render then re-parse ``fields`` and return the parsed mapping.

    Useful as a self-check: values that survive a render/parse cycle keep
    their type, making the round trip a cheap validation of the emitter.
    """
    parsed, _ = parse_frontmatter(render_frontmatter(fields))
    return parsed
