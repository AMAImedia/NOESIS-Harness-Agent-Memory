"""Deterministic long-context assembly with hard budgets and provenance."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Sequence, Tuple


@dataclass(frozen=True)
class ContextItem:
    item_id: str
    text: str
    priority: float = 0.0
    category: str = "evidence"
    source_ids: Tuple[str, ...] = ()
    required: bool = False


@dataclass(frozen=True)
class ContextAssembly:
    text: str
    used_tokens: int
    budget_tokens: int
    selected_ids: Tuple[str, ...]
    dropped_ids: Tuple[str, ...]
    source_ids: Tuple[str, ...]
    coverage: float


def estimate_tokens(text: str) -> int:
    """Conservative deterministic estimate; real providers may use a tokenizer."""
    return max(1, math.ceil(len(text) / 4)) if text else 0


class BudgetedContextAssembler:
    """Selects whole provenance-bearing blocks without ever exceeding the budget."""

    def __init__(self, budget_tokens: int, estimator: Callable[[str], int] = estimate_tokens):
        if budget_tokens < 1:
            raise ValueError("budget_tokens must be positive")
        self.budget_tokens = budget_tokens
        self.estimator = estimator

    def assemble(self, items: Sequence[ContextItem]) -> ContextAssembly:
        if not items:
            return ContextAssembly("", 0, self.budget_tokens, (), (), (), 1.0)
        unique={}
        for item in items:
            if not item.item_id or not item.text: continue
            unique.setdefault(item.item_id, item)
        ordered=sorted(unique.values(), key=lambda x: (not x.required, -x.priority, x.category != "pinned", x.item_id))
        selected=[]; dropped=[]; used=0; source_ids=[]
        total_value=sum(max(0.0, x.priority) for x in ordered) or 1.0
        selected_value=0.0
        for item in ordered:
            cost=max(1, int(self.estimator(item.text)))
            if cost <= self.budget_tokens - used:
                selected.append(item); used += cost; selected_value += max(0.0, item.priority); source_ids.extend(item.source_ids)
            else:
                dropped.append(item.item_id)
        rendered=[]
        for item in selected:
            rendered.append(f"[{item.category}:{item.item_id}]\n{item.text}")
        return ContextAssembly("\n\n".join(rendered), used, self.budget_tokens, tuple(x.item_id for x in selected), tuple(dropped), tuple(dict.fromkeys(source_ids)), min(1.0, selected_value / total_value))


__all__=["ContextItem", "ContextAssembly", "estimate_tokens", "BudgetedContextAssembler"]
