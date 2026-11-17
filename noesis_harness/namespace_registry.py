"""noesis_harness/namespace_registry.py

Deterministic namespace plus collision resolution for flat universal registries.

Provenance (patterns ported, not copied verbatim):
  - wshobson/agents, tools/adapters/codex.py: flat namespacing of shipped
    assets as ``<plugin>__<name>`` so every asset keeps a single, globally
    unique identifier even though plugins are authored independently.
  - wshobson/agents, tools/adapters/opencode.py, ``_opencode_skill_id``: the
    lower-cased, punctuation-normalized skill id built from a plugin prefix and
    a bare skill name.
  - wshobson/agents, tools/adapters/pi.py, ``pi_prompt_id`` / ``pi_agent_id``:
    the same prefix-plus-bare-name scheme for prompts and agents, including the
    collision case where the same bare name appears in more than one plugin.

A "flat universal registry" is a single dictionary keyed by a qualified id.
Because authors only pick the bare name, two plugins can ship a ``reviewer``;
the namespace prefix disambiguates them without renaming either asset. This
module reproduces that scheme with a deterministic sanitizer, a bounded
qualified id, and explicit collision reporting.

Determinism: sanitization is a pure character transform, every query returns a
sorted list or dict, JSON serialization sorts its keys and entries, and no
method reads the wall clock or any global state. Stdlib only; no I/O.
"""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple

__all__ = [
    "ALLOWED_RE",
    "MAX_NAME_LEN",
    "SEPARATOR",
    "NamespaceError",
    "NamespaceRegistry",
    "qualified",
    "sanitize",
]

SEPARATOR = "__"
MAX_NAME_LEN = 64
ALLOWED_RE = r"^[a-z0-9][a-z0-9._-]*$"

_ALLOWED_RE = re.compile(ALLOWED_RE)
_ALLOWED_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789._-")
_SEPARATOR_CHARS = "._-"
_TRIM_CHARS = "._-"
_REPEATED_SEPARATORS = re.compile(r"[._-]{2,}")
_EMPTY_NAME = "unnamed"


class NamespaceError(ValueError):
    """Raised for malformed input or a conflicting namespace registration."""


def sanitize(value: str) -> str:
    """Return the deterministic registry form of ``value``.

    The transform is, in order: lower-case; keep ``[a-z0-9._-]`` and replace
    every other character with ``-``; collapse any run of two or more separator
    characters (``.``, ``_``, ``-``) into a single ``-`` so a sanitized token
    can never contain the ``__`` separator; strip leading and trailing
    separators. A value that reduces to nothing becomes ``"unnamed"``.
    """
    if not isinstance(value, str):
        raise NamespaceError("value must be a string")

    lowered = value.lower()
    kept = []
    for char in lowered:
        if char in _ALLOWED_CHARS:
            kept.append(char)
        else:
            kept.append("-")
    collapsed = _REPEATED_SEPARATORS.sub("-", "".join(kept))
    trimmed = collapsed.strip(_TRIM_CHARS)
    if not trimmed:
        return _EMPTY_NAME
    return trimmed


def _rstrip_separators(value: str) -> str:
    """Return ``value`` with trailing separator characters removed."""
    return value.rstrip(_TRIM_CHARS)


def qualified(namespace: str, name: str) -> str:
    """Return the qualified id ``sanitize(namespace) + "__" + sanitize(name)``.

    The result is bounded by ``MAX_NAME_LEN``. The namespace and the separator
    are kept whenever the limit allows; only the trailing name is shortened, at
    a character boundary and with any trailing separator trimmed, so the ``__``
    separator is never split. When the sanitized namespace alone is too long to
    leave room for at least one name character, the namespace is shortened at a
    character boundary and a single name character is appended, again keeping
    the separator intact.
    """
    ns = sanitize(namespace)
    nm = sanitize(name)
    full = ns + SEPARATOR + nm
    if len(full) <= MAX_NAME_LEN:
        return full

    name_budget = MAX_NAME_LEN - len(ns) - len(SEPARATOR)
    if name_budget >= 1:
        return ns + SEPARATOR + _rstrip_separators(nm[:name_budget])

    ns_budget = MAX_NAME_LEN - len(SEPARATOR) - 1
    return _rstrip_separators(ns[:ns_budget]) + SEPARATOR + nm[:1]


def _validate_qualified_id(qualified_id: str) -> None:
    """Raise ``NamespaceError`` unless ``qualified_id`` is a well-formed id."""
    if not isinstance(qualified_id, str):
        raise NamespaceError("qualified id must be a string")
    if not qualified_id:
        raise NamespaceError("qualified id must not be empty")
    if _ALLOWED_RE.match(qualified_id) is None:
        raise NamespaceError("malformed qualified id: %r" % (qualified_id,))
    if SEPARATOR not in qualified_id:
        raise NamespaceError(
            "qualified id lacks the %r separator: %r" % (SEPARATOR, qualified_id)
        )


class NamespaceRegistry:
    """Flat ``<namespace>__<name>`` registry with explicit collision reporting.

    Each registered entry stores the raw namespace and name exactly as supplied
    by the caller, together with the sanitized bare name and the qualified id
    derived from them. Registration is idempotent for the same raw pair and
    raises ``NamespaceError`` when a *different* raw pair maps to an already
    used qualified id.
    """

    def __init__(self) -> None:
        self._entries = {}  # type: Dict[str, Dict]

    def register(self, namespace: str, name: str) -> str:
        """Register ``name`` under ``namespace`` and return the qualified id.

        Registering the same ``(namespace, name)`` pair twice is a no-op that
        returns the same id. A different pair that sanitizes to an already used
        qualified id raises ``NamespaceError``. Non-string inputs raise
        ``NamespaceError`` via :func:`sanitize`.
        """
        qualified_id = qualified(namespace, name)
        existing = self._entries.get(qualified_id)
        if existing is not None:
            if existing["namespace"] == namespace and existing["name"] == name:
                return qualified_id
            raise NamespaceError(
                "qualified id %r already belongs to (%r, %r), cannot reassign "
                "to (%r, %r)"
                % (
                    qualified_id,
                    existing["namespace"],
                    existing["name"],
                    namespace,
                    name,
                )
            )
        self._entries[qualified_id] = {
            "id": qualified_id,
            "namespace": namespace,
            "name": name,
            "bare": sanitize(name),
        }
        return qualified_id

    def resolve(self, qualified_id: str) -> Optional[Tuple[str, str]]:
        """Return the registered ``(namespace, name)`` pair, or ``None``.

        A malformed id (non-string, empty, not matching ``ALLOWED_RE``, or
        missing the separator) raises ``NamespaceError``; a well-formed but
        unregistered id returns ``None``. The returned pair is exactly what was
        passed to :meth:`register`.
        """
        _validate_qualified_id(qualified_id)
        entry = self._entries.get(qualified_id)
        if entry is None:
            return None
        return (entry["namespace"], entry["name"])

    def get(self, qualified_id: str) -> Optional[Dict]:
        """Return a copy of the entry for ``qualified_id``, or ``None``.

        The entry has keys ``id``, ``namespace``, ``name`` and ``bare``. The
        same malformed-versus-unknown rule as :meth:`resolve` applies.
        """
        _validate_qualified_id(qualified_id)
        entry = self._entries.get(qualified_id)
        if entry is None:
            return None
        return dict(entry)

    def bare_names(self) -> List[str]:
        """Return the sorted unique sanitized bare names in the registry."""
        return sorted({entry["bare"] for entry in self._entries.values()})

    def collisions(self) -> Dict[str, List[str]]:
        """Return bare names owned by more than one qualified id.

        The result maps each colliding bare name to its sorted qualified ids.
        Bare names with a single owner are omitted.
        """
        owners = {}  # type: Dict[str, List[str]]
        for qualified_id, entry in self._entries.items():
            owners.setdefault(entry["bare"], []).append(qualified_id)
        result = {}  # type: Dict[str, List[str]]
        for bare, ids in owners.items():
            if len(ids) > 1:
                result[bare] = sorted(ids)
        return result

    def disambiguate(self, name: str) -> List[str]:
        """Return the sorted qualified ids that own the bare name ``name``.

        ``name`` is sanitized before lookup, so the same rules that produced the
        stored bare names apply here. An unknown bare name yields an empty list.
        """
        bare = sanitize(name)
        return sorted(
            qualified_id
            for qualified_id, entry in self._entries.items()
            if entry["bare"] == bare
        )

    def ids(self) -> List[str]:
        """Return all qualified ids in sorted order."""
        return sorted(self._entries)

    def to_json(self) -> str:
        """Return a canonical JSON string for the registry.

        Keys and entries are sorted and separators are compact, so two
        registries with the same entries serialize identically regardless of
        registration order.
        """
        entries = [self._entries[qid] for qid in sorted(self._entries)]
        payload = {
            "version": 1,
            "entries": [
                {
                    "id": entry["id"],
                    "namespace": entry["namespace"],
                    "name": entry["name"],
                }
                for entry in entries
            ],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, text: str) -> "NamespaceRegistry":
        """Rebuild a registry from :meth:`to_json` output.

        Malformed JSON, an unknown schema version, or an entry whose id does
        not match the id derived from its namespace and name raises
        ``NamespaceError``.
        """
        if not isinstance(text, str):
            raise NamespaceError("registry json must be a string")
        try:
            payload = json.loads(text)
        except ValueError as exc:
            raise NamespaceError("invalid registry json: %s" % (exc,))
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise NamespaceError("unsupported registry json schema")
        entries = payload.get("entries")
        if not isinstance(entries, list):
            raise NamespaceError("registry entries must be a list")

        registry = cls()
        for item in entries:
            if not isinstance(item, dict):
                raise NamespaceError("registry entry must be an object")
            namespace = item.get("namespace")
            name = item.get("name")
            qualified_id = registry.register(namespace, name)
            expected = item.get("id")
            if expected is not None and expected != qualified_id:
                raise NamespaceError(
                    "registry entry id mismatch: %r != %r"
                    % (expected, qualified_id)
                )
        return registry
