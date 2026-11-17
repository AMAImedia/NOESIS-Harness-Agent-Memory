"""Tests for noesis_harness.elo_rank."""

import unittest

from noesis_harness.elo_rank import (
    DEFAULT_RATING,
    K_FACTOR,
    BootstrapCI,
    ConfidenceTier,
    EloTable,
    GoldCorpus,
    Match,
    bootstrap_ci,
    expected_score,
    select_references,
    update_ratings,
)


class TestExpectedScore(unittest.TestCase):

    def test_equal_ratings_is_half(self):
        self.assertEqual(expected_score(1000.0, 1000.0), 0.5)
        self.assertAlmostEqual(expected_score(DEFAULT_RATING, DEFAULT_RATING),
                               0.5)

    def test_symmetry(self):
        for a, b in [(1000.0, 1200.0), (1500.0, 900.0), (0.0, 400.0)]:
            self.assertAlmostEqual(expected_score(a, b) + expected_score(b, a),
                                   1.0)

    def test_higher_rating_is_favored(self):
        self.assertGreater(expected_score(1200.0, 1000.0), 0.5)
        self.assertLess(expected_score(1000.0, 1200.0), 0.5)


class TestUpdateRatings(unittest.TestCase):

    def test_zero_sum(self):
        a, b = update_ratings(1000.0, 1000.0, 1.0)
        self.assertAlmostEqual(a + b, 2000.0)

    def test_winner_gains_and_loser_loses(self):
        new_a, new_b = update_ratings(1000.0, 1000.0, 1.0)
        self.assertGreater(new_a, 1000.0)
        self.assertLess(new_b, 1000.0)
        self.assertAlmostEqual(new_a - 1000.0, 1000.0 - new_b)

    def test_draw_equal_ratings_is_neutral(self):
        self.assertEqual(update_ratings(1000.0, 1000.0, 0.5),
                         (1000.0, 1000.0))

    def test_score_a_validation(self):
        for bad in (-0.1, 0.3, 0.75, 1.1, "win", None, True):
            with self.assertRaises(ValueError):
                update_ratings(1000.0, 1000.0, bad)


class TestEloTable(unittest.TestCase):

    def test_default_rating_and_record(self):
        table = EloTable()
        self.assertEqual(table.rating("unknown"), DEFAULT_RATING)
        new_w, new_l = table.record("alice", "bob")
        self.assertAlmostEqual(new_w + new_l, 2 * DEFAULT_RATING)
        self.assertGreater(table.rating("alice"), DEFAULT_RATING)
        self.assertLess(table.rating("bob"), DEFAULT_RATING)

    def test_weight_scales_k(self):
        full = EloTable()
        half = EloTable()
        full.record("a", "b", weight=1.0)
        half.record("a", "b", weight=0.5)
        full_delta = full.rating("a") - DEFAULT_RATING
        half_delta = half.rating("a") - DEFAULT_RATING
        self.assertAlmostEqual(half_delta, full_delta / 2.0)

    def test_weight_above_one_is_clamped(self):
        clamped = EloTable()
        plain = EloTable()
        clamped.record("a", "b", weight=5.0)
        plain.record("a", "b", weight=1.0)
        self.assertAlmostEqual(clamped.rating("a"), plain.rating("a"))

    def test_invalid_weight_rejected(self):
        table = EloTable()
        for bad in (0.0, -1.0, "x", None):
            with self.assertRaises(ValueError):
                table.record("a", "b", weight=bad)

    def test_apply_order_determinism(self):
        matches = [
            Match("a", "b"),
            Match("b", "c", weight=0.5),
            Match("a", "c"),
        ]
        first = EloTable()
        second = EloTable()
        first.apply(matches)
        second.apply(list(matches))
        self.assertEqual(first.standings(), second.standings())

    def test_apply_order_matters(self):
        forward = EloTable()
        reverse = EloTable()
        forward.record("a", "b")
        forward.record("b", "c")
        reverse.record("b", "c")
        reverse.record("a", "b")
        self.assertNotEqual(forward.rating("c"), reverse.rating("c"))

    def test_standings_order(self):
        table = EloTable()
        table.record("alice", "bob")
        table.record("carol", "bob")
        standings = table.standings()
        names = [name for name, _rating in standings]
        ratings = [rating for _name, rating in standings]
        self.assertEqual(names, ["alice", "carol", "bob"])
        self.assertEqual(ratings, sorted(ratings, reverse=True))

    def test_standings_rating_tie_by_name(self):
        tie = EloTable()
        tie._ratings["beta"] = 1200.0
        tie._ratings["alpha"] = 1200.0
        self.assertEqual([n for n, _ in tie.standings()], ["alpha", "beta"])

    def test_badges(self):
        table = EloTable()
        table.record("alice", "bob")
        table.record("carol", "bob")
        badges = table.badges()
        self.assertEqual(badges["alice"], "gold")
        self.assertEqual(badges["carol"], "silver")
        self.assertEqual(badges["bob"], "bronze")

    def test_badges_empty_and_overflow(self):
        self.assertEqual(EloTable().badges(), {})
        table = EloTable()
        for name in ("a", "b", "c", "d"):
            table._ratings[name] = float(1000 - ord(name))
        badges = table.badges()
        self.assertEqual(badges["a"], "gold")
        self.assertEqual(badges["d"], "")

    def test_tier_for_boundaries(self):
        table = EloTable()
        self.assertEqual(table.tier_for(0), ConfidenceTier.ESTIMATED)
        self.assertEqual(table.tier_for(1), ConfidenceTier.MEASURED)
        self.assertEqual(table.tier_for(4), ConfidenceTier.MEASURED)
        self.assertEqual(table.tier_for(5), ConfidenceTier.CERTIFIED)
        self.assertEqual(table.tier_for(50), ConfidenceTier.CERTIFIED)

    def test_tier_for_invalid(self):
        table = EloTable()
        for bad in (-1, 1.5, "3", None, True):
            with self.assertRaises(ValueError):
                table.tier_for(bad)


class TestBootstrapCI(unittest.TestCase):

    def test_deterministic_same_seed(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        self.assertEqual(bootstrap_ci(values, seed=7),
                         bootstrap_ci(values, seed=7))

    def test_different_seed_varies(self):
        values = [float(i) for i in range(20)]
        self.assertNotEqual(bootstrap_ci(values, seed=1).low,
                            bootstrap_ci(values, seed=2).low)

    def test_percentiles_bounded(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        ci = bootstrap_ci(values, samples=100, seed=3)
        self.assertIsInstance(ci, BootstrapCI)
        self.assertLessEqual(ci.low, ci.mean)
        self.assertLessEqual(ci.mean, ci.high)
        self.assertGreaterEqual(ci.low, min(values))
        self.assertLessEqual(ci.high, max(values))

    def test_empty_bootstrap(self):
        self.assertEqual(bootstrap_ci([]), BootstrapCI(0.0, 0.0, 0.0))
        self.assertEqual(bootstrap_ci([], samples=10, seed=9),
                         BootstrapCI(0.0, 0.0, 0.0))


class TestGoldCorpus(unittest.TestCase):

    def test_sample_deterministic(self):
        corpus = GoldCorpus({"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0})
        self.assertEqual(corpus.sample(3, seed=42), corpus.sample(3, seed=42))
        self.assertEqual(len(corpus.sample(3, seed=42)), 3)

    def test_sample_clamps_and_orders(self):
        corpus = GoldCorpus({"a": 1.0, "b": 2.0})
        self.assertEqual(len(corpus.sample(10, seed=0)), 2)
        self.assertEqual(corpus.sample(0, seed=0), [])
        sampled = corpus.sample(2, seed=5)
        self.assertEqual(set(name for name, _ in sampled), {"a", "b"})

    def test_best(self):
        corpus = GoldCorpus({"a": 1.0, "b": 5.0, "c": 5.0})
        self.assertEqual(corpus.best(), "b")
        self.assertIsNone(GoldCorpus({}).best())


class TestSelectReferences(unittest.TestCase):

    def test_ordering(self):
        scores = {"low": 0.1, "top": 0.9, "mid": 0.5}
        self.assertEqual(select_references(scores, 2), ["top", "mid"])

    def test_tiebreak_by_name(self):
        scores = {"beta": 1.0, "alpha": 1.0, "gamma": 0.5}
        self.assertEqual(select_references(scores, 3),
                         ["alpha", "beta", "gamma"])

    def test_n_clamped(self):
        scores = {"a": 1.0, "b": 2.0}
        self.assertEqual(select_references(scores, 0), [])
        self.assertEqual(len(select_references(scores, 99)), 2)


if __name__ == "__main__":
    unittest.main()
