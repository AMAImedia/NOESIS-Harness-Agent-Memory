"""Tests for noesis_harness/context_budget.py (stdlib-only, deterministic)."""

from __future__ import annotations

import unittest

from noesis_harness.context_budget import estimate_tokens, fit


class TestEstimateTokens(unittest.TestCase):
    def test_empty_returns_zero(self):
        self.assertEqual(estimate_tokens(""), 0)

    def test_whitespace_returns_zero(self):
        self.assertEqual(estimate_tokens("   "), 0)

    def test_len_div_four_heuristic(self):
        self.assertEqual(estimate_tokens("abcd"), 1)
        self.assertEqual(estimate_tokens("abcdefgh"), 2)
        self.assertEqual(estimate_tokens("a"), 0)
        self.assertEqual(estimate_tokens("abc"), 0)

    def test_unicode_counts_code_points(self):
        # Four kanji -> len 4 -> 1 token estimate (len counts code points).
        self.assertEqual(estimate_tokens("\u3042\u3044\u3046\u3048"), 1)
        self.assertEqual(estimate_tokens("a\u3042cd"), 1)


class TestFit(unittest.TestCase):
    def test_empty_items_returns_empty(self):
        self.assertEqual(fit([], 100), [])

    def test_zero_budget_returns_empty(self):
        self.assertEqual(fit(["abcd", "efgh"], 0), [])

    def test_negative_budget_returns_empty(self):
        self.assertEqual(fit(["abcd"], -5), [])

    def test_under_budget_returns_all(self):
        items = ["abcd", "efgh", "ijkl"]
        self.assertEqual(fit(items, 100), items)

    def test_exact_budget_fits_all(self):
        # 4 items * 4 chars = 16 chars -> 4 tokens, budget exactly 4.
        items = ["abcd", "efgh", "ijkl", "mnop"]
        self.assertEqual(fit(items, 4), items)

    def test_over_budget_truncates_prefix(self):
        items = ["abcd", "efgh", "ijkl", "mnop"]
        # First two items (2 tokens) fit, third would push to 3 > budget 2.
        self.assertEqual(fit(items, 2), ["abcd", "efgh"])

    def test_fit_with_custom_key(self):
        items = [{"t": "abcd"}, {"t": "efgh"}, {"t": "ijkl"}]
        result = fit(items, 2, key=lambda d: d["t"])
        self.assertEqual(result, [{"t": "abcd"}, {"t": "efgh"}])

    def test_descending_priority_respected_by_order(self):
        # Larger items listed first (high priority); greedy prefix keeps the
        # most important ones and drops low-priority tail items.
        items = ["a" * 40, "b" * 40, "c" * 4]
        # budget 20 tokens: first two fit (20), third would exceed.
        self.assertEqual(fit(items, 20), ["a" * 40, "b" * 40])

    def test_determinism(self):
        items = ["abcd", "efgh", "ijkl", "mnop", "qrst"]
        self.assertEqual(fit(items, 3), fit(items, 3))


if __name__ == "__main__":
    unittest.main()
