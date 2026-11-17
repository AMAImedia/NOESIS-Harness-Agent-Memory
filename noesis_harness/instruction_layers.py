"""Deterministic instruction layers with a strict precedence chain.

Provenance: ported from the harness-books repository -- book1 chapter-02
("prompt is the control plane": instructions form a precedence chain where a
lower-authority layer can never override a higher-authority one), book2
chapter-02 (marked instruction fragments carrying ``{source, type,
precedence}`` metadata so every fragment is attributable) and book2 chapter-05
(layered long-lived instructions resolved by directory proximity, i.e. local
beats project beats user beats managed).

The module models a stack of :class:`InstructionFragment` objects. Each
fragment is tagged with a :class:`LayerSource` that carries a fixed base
authority, plus a signed ``precedence`` offset. Resolution sorts fragments by
effective precedence (base authority + offset) and renders them as one
deterministic document, inserting ``# <source>`` section headers whenever the
source changes.

The central safety invariant mirrors the prompt-as-control-plane rule: an
``append_only`` fragment is always rendered AFTER the base fragment of its own
source and can never remove or replace earlier text. Appending can extend the
instruction document but can never delete from it. The module is pure and
stdlib-only: no disk, no clock, no randomness, so a given fragment sequence
always resolves to the exact same string and digest.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class LayerSource(str, Enum):
    """Authority layer of an instruction fragment.

    Ordered from the lowest authority (``MANAGED``) to the highest
    (``RUNTIME``). The numeric authority of each member lives in
    :data:`PRECEDENCE`.
    """

    MANAGED = "managed"
    USER = "user"
    PROJECT = "project"
    LOCAL = "local"
    RUNTIME = "runtime"


PRECEDENCE: Dict[LayerSource, int] = {
    LayerSource.MANAGED: 10,
    LayerSource.USER: 20,
    LayerSource.PROJECT: 30,
    LayerSource.LOCAL: 40,
    LayerSource.RUNTIME: 50,
}


@dataclass(frozen=True)
class InstructionFragment:
    """A marked instruction fragment.

    Args:
        source: authority layer this fragment belongs to.
        text: instruction body. Must be non-empty after stripping.
        precedence: signed offset added to the source base authority; a lower
            effective precedence is rendered earlier.
        path: optional provenance path (e.g. the file the fragment came from).
        append_only: when True the fragment may only extend its source's text
            and is rendered after the source base.

    Raises:
        ValueError: if ``text`` is empty or whitespace-only.
    """

    source: LayerSource
    text: str
    precedence: int = 0
    path: str = ""
    append_only: bool = False

    def __post_init__(self):
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("InstructionFragment.text must be non-empty")
        object.__setattr__(self, "text", self.text.strip())


class InstructionStack:
    """A deterministic stack of instruction fragments.

    Fragments are resolved by ``(effective precedence, source rank, base
    before append, insertion order)`` where effective precedence is
    ``PRECEDENCE[source] + fragment.precedence``. To enforce the append-only
    invariant, an ``append_only`` fragment's effective precedence is clamped
    up to the lowest effective precedence of the base fragments of its own
    source (or to the source authority when it has no base). Together with the
    ``base before append`` tie-break this guarantees an append can never jump
    in front of the base text of its own source, even with a negative offset.
    """

    def __init__(self):
        self._fragments: List[InstructionFragment] = []
        self._counter = 0
        self._order: Dict[int, int] = {}

    def add(self, fragment: InstructionFragment) -> None:
        """Append a fragment to the stack.

        Raises:
            ValueError: if the fragment carries empty text.
        """
        if not isinstance(fragment.text, str) or not fragment.text.strip():
            raise ValueError("fragment text must be non-empty")
        self._fragments.append(fragment)
        self._order[id(fragment)] = self._counter
        self._counter += 1

    def _base_effective(self) -> Dict[LayerSource, int]:
        base: Dict[LayerSource, int] = {}
        for fragment in self._fragments:
            if fragment.append_only:
                continue
            effective = PRECEDENCE[fragment.source] + fragment.precedence
            current = base.get(fragment.source)
            if current is None or effective < current:
                base[fragment.source] = effective
        return base

    def _ordered(self) -> List[InstructionFragment]:
        base_effective = self._base_effective()

        def sort_key(fragment: InstructionFragment):
            effective = PRECEDENCE[fragment.source] + fragment.precedence
            if fragment.append_only:
                floor = base_effective.get(
                    fragment.source, PRECEDENCE[fragment.source]
                )
                if effective < floor:
                    effective = floor
            rank = PRECEDENCE[fragment.source]
            base_first = 1 if fragment.append_only else 0
            return (effective, rank, base_first, self._order[id(fragment)])

        return sorted(self._fragments, key=sort_key)

    def resolve(self) -> str:
        """Render the stack as a deterministic instruction document.

        Fragments are separated by a blank line. A ``# <source>`` header line
        is emitted only when the source changes between adjacent fragments in
        resolution order.
        """
        chunks: List[str] = []
        last_source: Optional[LayerSource] = None
        for fragment in self._ordered():
            if fragment.source != last_source:
                chunks.append("# " + fragment.source.value + "\n" + fragment.text)
                last_source = fragment.source
            else:
                chunks.append(fragment.text)
        return "\n\n".join(chunks)

    def base_for(self, source: LayerSource) -> Optional[str]:
        """Return the first non-append-only fragment text for ``source``.

        Returns:
            The base text, or None when the source has no base fragment.
        """
        for fragment in self._fragments:
            if fragment.source == source and not fragment.append_only:
                return fragment.text
        return None

    def fragments(self) -> List[InstructionFragment]:
        """Return the fragments in resolution order."""
        return self._ordered()

    def sources(self) -> List[LayerSource]:
        """Return the distinct sources present, sorted by authority ascending."""
        seen = set()
        for fragment in self._fragments:
            seen.add(fragment.source)
        return sorted(seen, key=lambda source: PRECEDENCE[source])

    def digest(self) -> str:
        """Return ``sha256:<hexdigest>`` of the resolved UTF-8 document."""
        payload = self.resolve().encode("utf-8")
        return "sha256:" + hashlib.sha256(payload).hexdigest()

    def append(
        self,
        source: LayerSource,
        text: str,
        precedence: int = 0,
    ) -> InstructionFragment:
        """Create and add an ``append_only`` fragment, returning it."""
        fragment = InstructionFragment(
            source=source,
            text=text,
            precedence=precedence,
            append_only=True,
        )
        self.add(fragment)
        return fragment


def assert_no_replacement(before: str, after: str) -> bool:
    """Return True when append-only resolution preserved every base line.

    Line-based semantics: split both documents on newlines, strip each line
    and ignore blank lines. The result is True when every non-blank line of
    ``before`` is equal to at least one non-blank line of ``after``. In other
    words appending may add lines but must not drop any existing one.
    """
    before_lines = [line.strip() for line in before.splitlines() if line.strip()]
    after_lines = set(line.strip() for line in after.splitlines() if line.strip())
    return all(line in after_lines for line in before_lines)


__all__ = [
    "LayerSource",
    "InstructionFragment",
    "PRECEDENCE",
    "InstructionStack",
    "assert_no_replacement",
]
