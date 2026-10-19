"""Three-valued authorization gate (allow | deny | ask) with sticky deny.

Provenance: ported from the harness-books repository -- book1 chapter-04
(tools-permissions-interrupts), book2 chapter-04 (approval decision tree) and
the appendix checklists. A boolean gate is forbidden by design: the third
value ASK keeps a human/operator in the loop whenever the outcome is neither
provably safe nor provably forbidden, and nothing in this module may silently
upgrade ASK into ALLOW.

The gate evaluates an ordered rule set against an action. Resolution rules:

* matching DENY outranks matching ASK, which outranks matching ALLOW;
* ties are broken by higher ``priority``, then by a longer (narrower) pattern,
  then by insertion order (the earlier-added rule wins);
* a rule whose ``tier`` is set only matches when the requested tier equals it,
  while a rule with ``tier=None`` matches every tier;
* with no matching rule the default is READ -> ALLOW, WRITE -> ASK and
  IRREVERSIBLE -> ASK, so an irreversible action is never allowed implicitly;
* once an ``action_id`` has been denied it is sticky and stays DENY for that
  id regardless of later rules or tiers.

Pattern syntax is intentionally tiny: an exact string match, or ``*`` segments
where each ``*`` matches any run of characters. Matching is case-sensitive, so
``Bash(git commit *)`` covers any commit command and ``Bash(npm:*)`` covers any
npm subcommand. The pattern ``*`` alone matches every action.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class Decision(str, Enum):
    """Tri-state gate outcome. ALLOW and DENY are terminal, ASK defers."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class RiskTier(str, Enum):
    """Coarse blast-radius classification of an action."""

    READ = "read"
    WRITE = "write"
    IRREVERSIBLE = "irreversible"


_RANK = {
    Decision.ALLOW: 0,
    Decision.ASK: 1,
    Decision.DENY: 2,
}

_DEFAULT_BY_TIER = {
    RiskTier.READ: Decision.ALLOW,
    RiskTier.WRITE: Decision.ASK,
    RiskTier.IRREVERSIBLE: Decision.ASK,
}


@dataclass(frozen=True)
class Rule:
    """One authorization rule.

    ``tier`` scopes the rule to a single risk tier when set. ``priority``
    breaks ties between equally ranked decisions. ``pattern`` uses the exact /
    trailing-``*`` syntax documented at module level. ``source`` is free-form
    provenance for auditing and does not affect resolution.
    """

    pattern: str
    decision: Decision
    tier: Optional[RiskTier] = None
    source: str = "default"
    priority: int = 0


def pattern_matches(pattern: str, action: str) -> bool:
    """Return whether ``pattern`` matches ``action`` (case-sensitive).

    Matching is exact unless the pattern contains ``*``. Each ``*`` matches any
    run of characters, including the empty run, so ``Bash(git commit *)``
    matches any commit command and ``Bash(npm:*)`` matches any npm subcommand.
    A ``*`` at the very end acts as a trailing prefix wildcard. The bare
    pattern ``*`` matches everything; characters other than ``*`` are literal.
    Multiple ``*`` segments must appear in order.
    """

    if pattern == "*":
        return True
    if "*" not in pattern:
        return pattern == action
    parts = pattern.split("*")
    head = parts[0]
    if head:
        if not action.startswith(head):
            return False
        position = len(head)
    else:
        position = 0
    tail = parts[-1]
    for part in parts[1:-1]:
        if not part:
            continue
        index = action.find(part, position)
        if index == -1:
            return False
        position = index + len(part)
    if tail:
        index = action.rfind(tail)
        if index == -1 or index < position or not action.endswith(tail):
            return False
    return True


class AuthorizationGate:
    """Ordered rule set plus sticky-deny memory for three-valued decisions."""

    def __init__(self) -> None:
        self._rules: List[Rule] = []
        self._sticky_denied: set = set()
        self._history: List[Tuple[str, str, Decision]] = []
        self._resolutions: List[Tuple[str, Decision]] = []

    def add_rule(self, rule: Rule) -> None:
        """Append a rule. Later additions never mutate earlier history."""

        if not isinstance(rule, Rule):
            raise TypeError("add_rule expects a Rule instance")
        self._rules.append(rule)

    def _rule_matches(self, rule: Rule, action: str, tier: RiskTier) -> bool:
        if rule.tier is not None and rule.tier != tier:
            return False
        return pattern_matches(rule.pattern, action)

    def _select(self, action: str, tier: RiskTier) -> Optional[Rule]:
        matches = [
            (index, rule)
            for index, rule in enumerate(self._rules)
            if self._rule_matches(rule, action, tier)
        ]
        if not matches:
            return None
        best = min(
            matches,
            key=lambda item: (
                -_RANK[item[1].decision],
                -item[1].priority,
                -len(item[1].pattern),
                item[0],
            ),
        )
        return best[1]

    def _resolve(self, action: str, tier: RiskTier) -> Decision:
        rule = self._select(action, tier)
        if rule is None:
            return _DEFAULT_BY_TIER[tier]
        return rule.decision

    def decide(
        self,
        action: str,
        tier: RiskTier = RiskTier.READ,
        action_id: Optional[str] = None,
    ) -> Decision:
        """Resolve ``action`` to a Decision and append it to history.

        A supplied ``action_id`` that was previously denied short-circuits to
        DENY (sticky deny). A DENY produced by the rules for a supplied
        ``action_id`` also makes that id sticky. ASK is never auto-escalated.
        """

        if not isinstance(tier, RiskTier):
            raise TypeError("tier must be a RiskTier")
        key = action_id if action_id is not None else ""
        if action_id is not None and action_id in self._sticky_denied:
            self._history.append((action, key, Decision.DENY))
            return Decision.DENY
        decision = self._resolve(action, tier)
        if decision is Decision.DENY and action_id is not None:
            self._sticky_denied.add(action_id)
        self._history.append((action, key, decision))
        return decision

    def is_sticky_denied(self, action_id: str) -> bool:
        """Return whether ``action_id`` is permanently denied."""

        return action_id in self._sticky_denied

    def record_ask_resolution(self, action_id: str, decision: Decision) -> None:
        """Record an operator's answer to a pending ASK.

        Only ALLOW or DENY are accepted. DENY becomes sticky; ALLOW is recorded
        but stays non-sticky, so future rule changes still apply. Passing ASK
        raises ``ValueError`` because an ASK can never resolve itself into
        another ASK without a human decision.
        """

        if not isinstance(decision, Decision):
            raise ValueError("resolution must be Decision.ALLOW or Decision.DENY")
        if decision is Decision.ASK:
            raise ValueError("ask never auto-escalates: resolution must be ALLOW or DENY")
        if decision is Decision.DENY:
            self._sticky_denied.add(action_id)
        self._resolutions.append((action_id, decision))

    def history(self) -> List[Tuple[str, str, Decision]]:
        """Return a copy of the append-only decision log in call order."""

        return list(self._history)


__all__ = [
    "AuthorizationGate",
    "Decision",
    "RiskTier",
    "Rule",
    "pattern_matches",
]
