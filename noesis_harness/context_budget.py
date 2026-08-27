"""noesis_harness/context_budget.py

Read-only token budgeting for context windows (LoopX). Provides a deterministic,
stdlib-only estimator and a greedy prefix fitter so a caller can pack the maximal
set of items that fits under a token budget without ever consulting an LLM.

Patterns borrowed: LoopX (deterministic budget projection, no external calls).
"""

from __future__ import annotations

from typing import List, Sequence, TypeVar

T = TypeVar("T")


def estimate_tokens(text: str) -> int:
    """Estimate the token count of ``text``.

    Uses the len/4 heuristic: every four characters count as roughly one token.
    The estimate is deterministic and pure. Empty or whitespace-only strings
    return 0. The result is always a non-negative integer.

    Args:
        text: The string to estimate. May be empty.

    Returns:
        Estimated integer token count (floor of len(text) / 4).
    """
    if not text:
        return 0
    return len(text) // 4


def fit(items: Sequence[T], budget: int, key=lambda item: item) -> List[T]:
    """Return the maximal prefix of ``items`` whose summed estimate <= ``budget``.

    Items are taken strictly in the order given; callers must pre-sort by
    priority if they want priority respected. Iteration stops at the first item
    whose inclusion would exceed the remaining budget, so the returned list is
    always a prefix of the input sequence. Determinism: identical inputs always
    yield identical outputs.

    Args:
        items: Ordered sequence of items to pack.
        budget: Non-negative integer token budget. Items are skipped once the
            running estimate would exceed this.
        key: Optional callable mapping an item to the text used for estimation.
            Defaults to identity (items must be strings).

    Returns:
        List of items forming the maximal fitting prefix.
    """
    if budget < 0:
        return []
    result: List[T] = []
    spent = 0
    for item in items:
        cost = estimate_tokens(key(item))
        if spent + cost > budget:
            break
        result.append(item)
        spent += cost
    return result
