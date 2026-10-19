"""noesis_harness/projection_adapters.py

Canonical source -> per-consumer adapters.

Pattern adapted from the wshobson/agents repository:
  - tools/adapters/base.py (HarnessAdapter.emit_plugin / emit_global: each
    harness owns the mechanical formatting of a shared canonical record)
  - tools/generate.py (dispatch over the registry of adapters)
  - tools/validate_generated.py (per-harness validation of generated output)

The idea ported here: one append-only canonical record is projected into many
derived consumer views. Every consumer view is produced by its own adapter,
which owns its format mechanics. The canonical source never carries
``if consumer == ...`` conditionals; adding a consumer means adding an adapter,
not editing the record.

The module is pure and side-effect free. It depends only on the Python
standard library (abc, dataclasses, hashlib, json, typing) so it can be
imported anywhere in the harness.

Consumer output contract
------------------------
Every adapter emits a dict with at least:
  - ``filename``: a relative artifact path (slug derived from ``record["name"]``)
  - ``content``: the serialized body in the adapter's own format

``Consumer.render`` (not ``emit``) is what the registry calls: it wraps
``emit`` and stamps ``consumer`` and ``source_digest`` so derived artifacts can
be traced back to the exact canonical record that produced them.

TOML note: there is no TOML writer in the standard library, so ``TomlAdapter``
hand-rolls a deliberately small subset: ``title = "..."`` plus flat
``key = value`` lines and lists of scalars. Nested dictionaries are skipped
(``None`` values and unsupported containers are skipped as well).
"""

from __future__ import annotations

import abc
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

VALID_SEVERITIES = ("error", "warning", "info")

_EXPECTED_SUFFIX = {
    "markdown": ".md",
    "json": ".json",
    "toml": ".toml",
}


def slugify(value: str) -> str:
    """Return a deterministic, filename-safe slug for ``value``.

    Lowercases the input, replaces every non-alphanumeric character with a
    hyphen, collapses runs of hyphens, and strips leading/trailing hyphens.
    An empty (or all-separator) result becomes ``"untitled"``.
    """
    chars = []
    for char in value.lower():
        chars.append(char if char.isalnum() else "-")
    slug = "".join(chars)
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = slug.strip("-")
    return slug or "untitled"


def canonical_digest(value: Any) -> str:
    """Return ``"sha256:" + sha256(canonical JSON of value)``.

    Canonical form is ``json.dumps(sort_keys=True, ensure_ascii=False,
    default=str)``: stable across dict key order and across runs, with
    non-serializable leaves reduced through ``str``.
    """
    payload = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Finding:
    """A single validation finding for one generated artifact.

    ``severity`` is one of ``"error"``, ``"warning"``, ``"info"``.
    ``remediation`` must be a non-empty instruction describing how to fix the
    finding; an empty remediation is a programming error and raises.
    """

    severity: str
    consumer: str
    message: str
    remediation: str

    def __post_init__(self) -> None:
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                "severity must be one of %r, got %r"
                % (VALID_SEVERITIES, self.severity)
            )
        if not self.remediation:
            raise ValueError("remediation must be non-empty")


class Consumer(abc.ABC):
    """One derived view of the canonical record.

    Subclasses implement ``name`` and ``emit`` only; ``render`` is the stable
    entry point used by :class:`AdapterRegistry` and adds provenance.
    """

    @abc.abstractmethod
    def name(self) -> str:
        """Return the unique consumer name (registry key)."""
        raise NotImplementedError

    @abc.abstractmethod
    def emit(self, record: Dict) -> Dict:
        """Return the format-specific artifact for ``record``.

        The result must be a dict carrying ``filename`` and ``content``.
        """
        raise NotImplementedError

    def render(self, record: Dict) -> Dict:
        """Call ``emit`` and stamp consumer name + source digest.

        The canonical record is never mutated. A shallow copy of the emitted
        artifact is returned so adapter internals stay untouched.
        """
        artifact = dict(self.emit(record))
        artifact["consumer"] = self.name()
        artifact["source_digest"] = canonical_digest(record)
        return artifact


def _record_title(record: Dict) -> str:
    """Resolve a human title for the record (title, else name, else "")."""
    for key in ("title", "name"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _record_body(record: Dict) -> str:
    """Resolve the markdown body (body, description, summary, else "")."""
    for key in ("body", "description", "summary"):
        value = record.get(key)
        if isinstance(value, str):
            return value
    return ""


class MarkdownAdapter(Consumer):
    """Emit a Markdown artifact with a YAML frontmatter title."""

    def name(self) -> str:
        return "markdown"

    def emit(self, record: Dict) -> Dict:
        slug = slugify(str(record.get("name") or ""))
        title = _record_title(record).replace("\n", " ").strip()
        body = _record_body(record)
        content = "---\ntitle: %s\n---\n\n%s" % (title, body)
        return {"filename": slug + ".md", "content": content}


class JsonAdapter(Consumer):
    """Emit the canonical record as canonical JSON text."""

    def name(self) -> str:
        return "json"

    def emit(self, record: Dict) -> Dict:
        slug = slugify(str(record.get("name") or ""))
        content = json.dumps(
            record,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        return {"filename": slug + ".json", "content": content}


def _toml_string(value: str) -> str:
    """Quote and escape a string for the hand-rolled TOML subset."""
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return '"%s"' % escaped


def _toml_scalar(value: Any) -> Optional[str]:
    """Render a scalar TOML value, or ``None`` when unsupported."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return _toml_string(value)
    return None


def _toml_value(value: Any) -> Optional[str]:
    """Render a supported TOML value (scalar or list of scalars)."""
    if isinstance(value, list):
        rendered = []
        for item in value:
            if isinstance(item, list) or isinstance(item, dict):
                return None
            scalar = _toml_scalar(item)
            if scalar is None:
                return None
            rendered.append(scalar)
        return "[" + ", ".join(rendered) + "]"
    return _toml_scalar(value)


class TomlAdapter(Consumer):
    """Emit a small hand-rolled TOML document.

    Emits ``title = "..."`` first, then one ``key = value`` line per scalar
    field (sorted by key) and ``key = ["a", "b"]`` for lists of scalars.
    Nested dictionaries, ``None`` values, and unsupported containers are
    skipped.
    """

    def name(self) -> str:
        return "toml"

    def emit(self, record: Dict) -> Dict:
        slug = slugify(str(record.get("name") or ""))
        lines: List[str] = ["title = %s" % _toml_string(_record_title(record))]
        for key in sorted(record):
            if key == "title":
                continue
            value = record[key]
            if value is None or isinstance(value, dict):
                continue
            rendered = _toml_value(value)
            if rendered is None:
                continue
            lines.append("%s = %s" % (key, rendered))
        return {"filename": slug + ".toml", "content": "\n".join(lines)}


class AdapterRegistry:
    """Ordered collection of adapters plus validation over their output."""

    def __init__(self) -> None:
        self._adapters: Dict[str, Consumer] = {}

    def register(self, adapter: Consumer) -> None:
        """Register ``adapter``; a duplicate name raises ``ValueError``."""
        adapter_name = adapter.name()
        if adapter_name in self._adapters:
            raise ValueError("adapter already registered: %s" % adapter_name)
        self._adapters[adapter_name] = adapter

    def names(self) -> List[str]:
        """Return all registered consumer names, sorted."""
        return sorted(self._adapters)

    def get(self, name: str) -> Consumer:
        """Return the adapter registered under ``name`` (``KeyError`` if absent)."""
        if name not in self._adapters:
            raise KeyError(name)
        return self._adapters[name]

    def emit(
        self,
        record: Dict,
        consumers: Optional[Iterable[str]] = None,
    ) -> Dict[str, Dict]:
        """Render ``record`` for the requested consumers.

        ``consumers`` defaults to every registered consumer. Processing order
        is sorted by consumer name, so the returned mapping is deterministic.
        An unknown consumer name raises ``KeyError``.
        """
        if consumers is None:
            selected = self.names()
        else:
            selected = sorted(consumers)
        artifacts: Dict[str, Dict] = {}
        for consumer_name in selected:
            artifacts[consumer_name] = self.get(consumer_name).render(record)
        return artifacts

    def validate(self, artifacts: Dict[str, Dict]) -> List[Finding]:
        """Validate rendered artifacts and return findings, sorted by consumer.

        Checks each artifact against the structural contract shared by all
        adapters (non-empty ``filename`` and ``content``, matching extension,
        provenance fields). Unknown consumers are errors. The function is
        pure: it does not raise on malformed artifacts, it reports findings.
        """
        findings: List[Finding] = []
        for consumer_name in sorted(artifacts):
            artifact = artifacts[consumer_name]
            if consumer_name not in self._adapters:
                findings.append(
                    Finding(
                        severity="error",
                        consumer=consumer_name,
                        message="artifact produced by an unknown consumer",
                        remediation=(
                            "Register a Consumer named %r before validating its "
                            "artifacts." % consumer_name
                        ),
                    )
                )
                continue
            if not isinstance(artifact, dict):
                findings.append(
                    Finding(
                        severity="error",
                        consumer=consumer_name,
                        message="artifact is not a mapping",
                        remediation=(
                            "Re-render with consumer %r so it returns a dict with "
                            "'filename' and 'content'." % consumer_name
                        ),
                    )
                )
                continue
            filename = artifact.get("filename")
            if not isinstance(filename, str) or not filename.strip():
                findings.append(
                    Finding(
                        severity="error",
                        consumer=consumer_name,
                        message="artifact is missing a non-empty filename",
                        remediation=(
                            "Adapter %r must emit a non-empty 'filename' derived "
                            "from slugify(record['name'])." % consumer_name
                        ),
                    )
                )
            else:
                expected = _EXPECTED_SUFFIX.get(consumer_name)
                if expected is not None and not filename.endswith(expected):
                    findings.append(
                        Finding(
                            severity="warning",
                            consumer=consumer_name,
                            message="filename %r does not end with %r"
                            % (filename, expected),
                            remediation=(
                                "Rename the artifact to end with %r for consumer "
                                "%r." % (expected, consumer_name)
                            ),
                        )
                    )
            content = artifact.get("content")
            if not isinstance(content, str) or content == "":
                findings.append(
                    Finding(
                        severity="error",
                        consumer=consumer_name,
                        message="artifact is missing non-empty content",
                        remediation=(
                            "Adapter %r must emit a non-empty 'content' string."
                            % consumer_name
                        ),
                    )
                )
            if artifact.get("consumer") != consumer_name:
                findings.append(
                    Finding(
                        severity="warning",
                        consumer=consumer_name,
                        message="artifact provenance consumer does not match",
                        remediation=(
                            "Render through Consumer.render so 'consumer' is "
                            "stamped as %r." % consumer_name
                        ),
                    )
                )
            if not artifact.get("source_digest"):
                findings.append(
                    Finding(
                        severity="warning",
                        consumer=consumer_name,
                        message="artifact is missing source_digest provenance",
                        remediation=(
                            "Render through Consumer.render so 'source_digest' is "
                            "stamped from canonical_digest(record)."
                        ),
                    )
                )
        return findings


def emit_all(
    record: Dict,
    registry: AdapterRegistry,
    consumers: Optional[Iterable[str]] = None,
) -> Dict[str, Dict]:
    """Render ``record`` for ``consumers`` via ``registry``.

    Thin delegate over :meth:`AdapterRegistry.emit`, kept as the module-level
    entry point mirroring the wshobson/agents ``generate.py`` dispatch.
    """
    return registry.emit(record, consumers)


def default_registry() -> AdapterRegistry:
    """Return a registry with the markdown, json, and toml adapters."""
    registry = AdapterRegistry()
    registry.register(MarkdownAdapter())
    registry.register(JsonAdapter())
    registry.register(TomlAdapter())
    return registry


__all__ = [
    "VALID_SEVERITIES",
    "Consumer",
    "AdapterRegistry",
    "Finding",
    "MarkdownAdapter",
    "JsonAdapter",
    "TomlAdapter",
    "slugify",
    "canonical_digest",
    "emit_all",
    "default_registry",
]
