"""Controlled legacy-vs-nextgen memory evaluation under identical budgets."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple

from .context_engine import BudgetedContextAssembler, ContextItem, estimate_tokens


@dataclass(frozen=True)
class MemoryABCase:
    case_id: str
    query: str
    relevant_source_ids: Tuple[str, ...]
    budget_tokens: int
    legacy_items: Tuple[ContextItem, ...]
    nextgen_items: Tuple[ContextItem, ...]


@dataclass(frozen=True)
class MemoryABOutcome:
    case_id: str
    budget_tokens: int
    legacy_used_tokens: int
    nextgen_used_tokens: int
    legacy_selected_ids: Tuple[str, ...]
    nextgen_selected_ids: Tuple[str, ...]
    legacy_source_ids: Tuple[str, ...]
    nextgen_source_ids: Tuple[str, ...]
    legacy_recall: float
    nextgen_recall: float
    transfer_gain: float
    nextgen_dropped_ids: Tuple[str, ...]
    hard_cap_respected: bool


class ControlledMemoryEvaluator:
    """Compare memory representations without changing model or token budget."""

    def __init__(self, estimator=estimate_tokens):
        self.estimator = estimator

    @staticmethod
    def _legacy_prefix(items: Sequence[ContextItem], budget: int, estimator) -> Tuple[Tuple[ContextItem, ...], int]:
        selected = []
        used = 0
        for item in items:
            cost = max(1, int(estimator(item.text)))
            if cost <= budget - used:
                selected.append(item)
                used += cost
        return tuple(selected), used

    @staticmethod
    def _recall(source_ids: Iterable[str], relevant: Sequence[str]) -> float:
        relevant_set = set(relevant)
        if not relevant_set:
            return 1.0
        return len(set(source_ids) & relevant_set) / len(relevant_set)

    def evaluate_case(self, case: MemoryABCase) -> MemoryABOutcome:
        if not case.case_id or case.budget_tokens < 1:
            raise ValueError("case_id and positive budget_tokens are required")
        legacy, legacy_used = self._legacy_prefix(case.legacy_items, case.budget_tokens, self.estimator)
        assembly = BudgetedContextAssembler(case.budget_tokens, self.estimator).assemble(case.nextgen_items)
        legacy_sources = tuple(dict.fromkeys(source for item in legacy for source in item.source_ids))
        legacy_recall = self._recall(legacy_sources, case.relevant_source_ids)
        return MemoryABOutcome(
            case_id=case.case_id,
            budget_tokens=case.budget_tokens,
            legacy_used_tokens=legacy_used,
            nextgen_used_tokens=assembly.used_tokens,
            legacy_selected_ids=tuple(item.item_id for item in legacy),
            nextgen_selected_ids=assembly.selected_ids,
            legacy_source_ids=legacy_sources,
            nextgen_source_ids=assembly.source_ids,
            legacy_recall=legacy_recall,
            nextgen_recall=self._recall(assembly.source_ids, case.relevant_source_ids),
            transfer_gain=self._recall(assembly.source_ids, case.relevant_source_ids) - legacy_recall,
            nextgen_dropped_ids=assembly.dropped_ids,
            hard_cap_respected=assembly.used_tokens <= case.budget_tokens,
        )

    def evaluate(self, cases: Sequence[MemoryABCase]) -> Tuple[MemoryABOutcome, ...]:
        return tuple(self.evaluate_case(case) for case in cases)


__all__ = ["ControlledMemoryEvaluator", "MemoryABCase", "MemoryABOutcome"]
