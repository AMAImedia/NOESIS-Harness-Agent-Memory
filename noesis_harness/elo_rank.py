"""Deterministic Elo ranking with bootstrap confidence intervals.

Provenance (patterns ported, not copied verbatim):
- wshobson/agents, ``plugins/plugin-eval/src/plugin_eval/elo.py``: the
  standard Elo logistic ``expected_score``, zero-sum ``update_ratings`` and a
  mutable rating table keyed by player name.
- wshobson/agents, ``plugins/plugin-eval/src/plugin_eval/corpus.py``,
  ``select_references``: top-n reference selection by descending score with a
  name tiebreak.
- wshobson/agents, ``plugins/plugin_eval/src/plugin_eval/models.py``: badge
  assignment by rank and confidence tiers (estimated / measured / certified)
  derived from the number of matches played.

Determinism and purity: no wall-clock reads, no global mutable state and no
implicit randomness. ``bootstrap_ci`` and ``GoldCorpus.sample`` take an
explicit integer seed and drive ``random.Random(seed)`` only, so identical
inputs always produce identical outputs. Stdlib only.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Optional, Tuple

DEFAULT_RATING = 1000.0
K_FACTOR = 32.0

_BADGE_BY_RANK = ("gold", "silver", "bronze")

__all__ = [
    "DEFAULT_RATING",
    "K_FACTOR",
    "expected_score",
    "update_ratings",
    "Match",
    "EloTable",
    "ConfidenceTier",
    "BootstrapCI",
    "bootstrap_ci",
    "GoldCorpus",
    "select_references",
]


def _validate_rating(rating: float, field: str) -> float:
    """Return ``rating`` as a float, raising ``ValueError`` when invalid."""
    if isinstance(rating, bool) or not isinstance(rating, (int, float)):
        raise ValueError("elo_rating_invalid:" + field)
    return float(rating)


def _clamp_weight(weight: float) -> float:
    """Clamp a match weight into the closed-open interval (0, 1].

    Weights greater than one are capped at one; non-positive or non-numeric
    weights are rejected because they carry no ranking signal.
    """
    if isinstance(weight, bool) or not isinstance(weight, (int, float)):
        raise ValueError("elo_match_weight_invalid")
    if weight <= 0.0:
        raise ValueError("elo_match_weight_invalid")
    return float(min(1.0, weight))


def expected_score(rating_a: float, rating_b: float) -> float:
    """Standard Elo logistic expectation for player A against player B."""
    a = _validate_rating(rating_a, "rating_a")
    b = _validate_rating(rating_b, "rating_b")
    return 1.0 / (1.0 + (10.0 ** ((b - a) / 400.0)))


def update_ratings(rating_a: float, rating_b: float, score_a: float,
                   k: float = K_FACTOR) -> Tuple[float, float]:
    """Return ``(new_a, new_b)`` after a single zero-sum Elo update.

    ``score_a`` must be one of ``0.0`` (A lost), ``0.5`` (draw) or ``1.0``
    (A won). ``k`` is the rating volatility; the winner's gain equals the
    loser's loss, so the pair sum is preserved exactly.
    """
    a = _validate_rating(rating_a, "rating_a")
    b = _validate_rating(rating_b, "rating_b")
    if isinstance(score_a, bool) or not isinstance(score_a, (int, float)):
        raise ValueError("elo_score_a_invalid")
    if float(score_a) not in (0.0, 0.5, 1.0):
        raise ValueError("elo_score_a_invalid")
    k = _validate_rating(k, "k")
    if k < 0.0:
        raise ValueError("elo_k_invalid")

    expected_a = expected_score(a, b)
    delta = k * (float(score_a) - expected_a)
    return a + delta, b - delta


@dataclass(frozen=True)
class Match:
    """A single head-to-head result.

    ``weight`` scales the effective K factor for this match and must lie in
    the interval (0, 1]; values above one are clamped to one.
    """

    winner: str
    loser: str
    weight: float = 1.0


class ConfidenceTier(str, Enum):
    """How much evidence backs a rating.

    ``ESTIMATED`` means no matches have been played, ``MEASURED`` covers one
    to four matches, and ``CERTIFIED`` requires at least five matches.
    """

    ESTIMATED = "estimated"
    MEASURED = "measured"
    CERTIFIED = "certified"


@dataclass(frozen=True)
class BootstrapCI:
    """Percentile confidence interval for a bootstrap of means."""

    low: float
    high: float
    mean: float


class EloTable:
    """Mutable, order-sensitive Elo rating table.

    Ratings start at ``default``. Every player is tracked together with the
    number of matches they have played. Updates are deterministic functions
    of the applied match order; no implicit time or randomness is involved.
    """

    def __init__(self, k: float = K_FACTOR, default: float = DEFAULT_RATING):
        self._k = _validate_rating(k, "k")
        if self._k < 0.0:
            raise ValueError("elo_k_invalid")
        self._default = _validate_rating(default, "default")
        self._ratings: Dict[str, float] = {}
        self._played: Dict[str, int] = {}

    def rating(self, player: str) -> float:
        """Current rating for ``player`` (``default`` when unseen)."""
        if not isinstance(player, str) or not player:
            raise ValueError("elo_player_invalid")
        return self._ratings.get(player, self._default)

    def played(self, player: str) -> int:
        """Number of matches recorded for ``player``."""
        if not isinstance(player, str) or not player:
            raise ValueError("elo_player_invalid")
        return self._played.get(player, 0)

    def record(self, winner: str, loser: str,
               weight: float = 1.0) -> Tuple[float, float]:
        """Record a win for ``winner`` over ``loser`` and return new ratings."""
        if not isinstance(winner, str) or not winner:
            raise ValueError("elo_winner_invalid")
        if not isinstance(loser, str) or not loser:
            raise ValueError("elo_loser_invalid")
        if winner == loser:
            raise ValueError("elo_self_match_invalid")
        w = _clamp_weight(weight)

        rating_a = self.rating(winner)
        rating_b = self.rating(loser)
        new_a, new_b = update_ratings(rating_a, rating_b, 1.0,
                                      k=self._k * w)
        self._ratings[winner] = new_a
        self._ratings[loser] = new_b
        self._played[winner] = self._played.get(winner, 0) + 1
        self._played[loser] = self._played.get(loser, 0) + 1
        return new_a, new_b

    def apply(self, matches: Iterable[Match]) -> None:
        """Apply matches in input order, weighting each one's K factor."""
        for match in matches:
            self.record(match.winner, match.loser, match.weight)

    def standings(self) -> List[Tuple[str, float]]:
        """All known players sorted by rating desc then name asc."""
        return sorted(self._ratings.items(),
                      key=lambda item: (-item[1], item[0]))

    def badges(self) -> Dict[str, str]:
        """Rank badges: gold, silver and bronze for the top three, else ''."""
        result: Dict[str, str] = {}
        for rank, (player, _rating) in enumerate(self.standings()):
            result[player] = (
                _BADGE_BY_RANK[rank] if rank < len(_BADGE_BY_RANK) else ""
            )
        return result

    def tier_for(self, matches_played: int) -> ConfidenceTier:
        """Confidence tier for a given number of played matches."""
        if isinstance(matches_played, bool) or not isinstance(matches_played, int):
            raise ValueError("elo_matches_played_invalid")
        if matches_played < 0:
            raise ValueError("elo_matches_played_invalid")
        if matches_played == 0:
            return ConfidenceTier.ESTIMATED
        if matches_played < 5:
            return ConfidenceTier.MEASURED
        return ConfidenceTier.CERTIFIED


def _nearest_rank(sorted_values: List[float], percentile: float) -> float:
    """Nearest-rank percentile (1-based rank) on an ascending list."""
    count = len(sorted_values)
    rank = int(math.ceil((percentile / 100.0) * count))
    if rank < 1:
        rank = 1
    if rank > count:
        rank = count
    return sorted_values[rank - 1]


def bootstrap_ci(values: List[float], samples: int = 200,
                 seed: int = 0) -> BootstrapCI:
    """Bootstrap the mean of ``values`` and return its 5th/95th percentiles.

    Resampling is driven solely by ``random.Random(seed)``, so the result is
    reproducible for a given seed and input. An empty input (or a
    non-positive sample count) yields ``BootstrapCI(0.0, 0.0, 0.0)``.
    """
    data = [float(v) for v in values]
    if not data or samples <= 0:
        return BootstrapCI(0.0, 0.0, 0.0)

    rng = random.Random(seed)
    size = len(data)
    means: List[float] = []
    for _ in range(samples):
        total = 0.0
        for _ in range(size):
            total += data[rng.randrange(size)]
        means.append(total / size)

    means.sort()
    mean_of_means = math.fsum(means) / len(means)
    return BootstrapCI(
        low=_nearest_rank(means, 5.0),
        high=_nearest_rank(means, 95.0),
        mean=mean_of_means,
    )


def _deterministic_sample(names: List[str], n: int,
                          rng: random.Random) -> List[str]:
    """Partial Fisher-Yates shuffle: deterministic for a seeded RNG."""
    pool = list(names)
    count = len(pool)
    k = min(max(n, 0), count)
    for i in range(k):
        j = rng.randrange(i, count)
        pool[i], pool[j] = pool[j], pool[i]
    return pool[:k]


class GoldCorpus:
    """Named references with numeric gold scores.

    ``sample`` returns a deterministic, seed-driven subset; ``best`` returns
    the highest-scoring name, breaking ties by ascending name.
    """

    def __init__(self, references: Dict[str, float]):
        if not isinstance(references, dict):
            raise ValueError("gold_corpus_references_invalid")
        cleaned: Dict[str, float] = {}
        for name, score in references.items():
            if not isinstance(name, str) or not name:
                raise ValueError("gold_corpus_reference_invalid")
            cleaned[name] = _validate_rating(score, "reference_score")
        self._references = cleaned

    def _names(self) -> List[str]:
        return sorted(self._references)

    def sample(self, n: int, seed: int = 0) -> List[Tuple[str, float]]:
        """Return ``n`` seed-deterministic ``(name, score)`` pairs."""
        if isinstance(n, bool) or not isinstance(n, int):
            raise ValueError("gold_corpus_n_invalid")
        rng = random.Random(seed)
        chosen = _deterministic_sample(self._names(), n, rng)
        return [(name, self._references[name]) for name in chosen]

    def best(self) -> Optional[str]:
        """Highest-scoring reference name, ties broken by ascending name."""
        best_name: Optional[str] = None
        best_score: Optional[float] = None
        for name in self._names():
            score = self._references[name]
            if best_score is None or score > best_score:
                best_score = score
                best_name = name
        return best_name


def select_references(scores: Dict[str, float], n: int,
                      seed: int = 0) -> List[str]:
    """Return the top ``n`` names by score desc then name asc.

    ``seed`` is accepted for API parity with the upstream helper but is not
    used: the ordering is a total, deterministic order.
    """
    if not isinstance(scores, dict):
        raise ValueError("select_references_scores_invalid")
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("select_references_n_invalid")
    ordered = sorted(scores.items(), key=lambda item: (-float(item[1]),
                                                       item[0]))
    return [name for name, _score in ordered[:max(n, 0)]]
