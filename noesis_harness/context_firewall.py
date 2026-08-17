"""Taint-aware context assembly with deny-by-default restricted data."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Tuple

from .resource_lineage import SENSITIVITIES


@dataclass(frozen=True)
class ContextItem:
    item_id: str
    content: str
    sensitivity: str
    scope: str = "local"
    resource_id: str = ""


@dataclass(frozen=True)
class ContextDecision:
    text: str
    included_ids: Tuple[str, ...]
    redacted_ids: Tuple[str, ...]
    truncated_ids: Tuple[str, ...]
    digest: str
    included_resource_ids: Tuple[str, ...] = ()


class ContextFirewall:
    """Build bounded model context without silently crossing sensitivity scope."""

    def build(self, items: Iterable[ContextItem], *, allowed_sensitivities: Tuple[str, ...] = ("public", "internal"), allowed_scopes: Tuple[str, ...] = ("local",), max_chars: int = 12000, explicit_approval: bool = False) -> ContextDecision:
        if max_chars <= 0:
            raise ValueError("max_chars must be positive")
        if not set(allowed_sensitivities).issubset(SENSITIVITIES):
            raise ValueError("unknown sensitivity")
        if not allowed_scopes or any(not isinstance(scope, str) or not scope.strip() for scope in allowed_scopes):
            raise ValueError("invalid allowed_scopes")
        allowed = set(allowed_sensitivities)
        scopes = set(allowed_scopes)
        included, redacted, truncated, included_resources, chunks = [], [], [], [], []
        used = 0
        for item in items:
            if not item.item_id or not item.scope or item.sensitivity not in SENSITIVITIES:
                raise ValueError("invalid context item")
            if item.sensitivity not in allowed or item.scope not in scopes:
                if not explicit_approval:
                    redacted.append(item.item_id)
                    continue
            fragment = item.content
            separator = "\n\n" if chunks else ""
            remaining = max_chars - used - len(separator)
            if remaining <= 0:
                truncated.append(item.item_id)
                continue
            if len(fragment) > remaining:
                chunks.append(separator + fragment[:remaining])
                included.append(item.item_id)
                included_resources.append(item.resource_id)
                truncated.append(item.item_id)
                used = max_chars
                continue
            chunks.append(separator + fragment)
            included.append(item.item_id)
            included_resources.append(item.resource_id)
            used += len(separator) + len(fragment)
        text = "".join(chunks)
        digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        return ContextDecision(text, tuple(included), tuple(redacted), tuple(truncated), digest, tuple(included_resources))


__all__ = ["ContextDecision", "ContextFirewall", "ContextItem"]
