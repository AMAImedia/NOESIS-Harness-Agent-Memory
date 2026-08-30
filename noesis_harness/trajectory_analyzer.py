"""noesis_harness/trajectory_analyzer.py — trajectory pattern analysis.

Patterns: LoopX trajectory analysis.
Stdlib only.
"""
from __future__ import annotations
from typing import Any, Dict, List, Tuple

class TrajectoryAnalyzer:
    def __init__(self):
        self._success: List[Dict] = []
        self._failure: List[Dict] = []

    def record(self, trajectory: Dict[str, Any], outcome: str) -> None:
        if outcome == "success": self._success.append(dict(trajectory))
        elif outcome == "failure": self._failure.append(dict(trajectory))

    def _avg(self, data: List[Dict], key: str) -> float:
        vals = [d[key] for d in data if isinstance(d.get(key), (int, float))]
        return sum(vals) / len(vals) if vals else 0.0

    def _count_actions(self, data: List[Dict]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for d in data:
            for a in d.get("actions", []):
                counts[a] = counts.get(a, 0) + 1
        return counts

    def diff(self) -> Dict[str, Any]:
        if not self._success or not self._failure:
            return {"status": "insufficient_data"}
        s_actions = self._count_actions(self._success)
        f_actions = self._count_actions(self._failure)
        all_actions = set(s_actions) | set(f_actions)
        action_diff = {}
        for a in all_actions:
            s_rate = s_actions.get(a, 0) / max(len(self._success), 1)
            f_rate = f_actions.get(a, 0) / max(len(self._failure), 1)
            action_diff[a] = round(s_rate - f_rate, 3)
        return {
            "status": "ok",
            "success_count": len(self._success),
            "failure_count": len(self._failure),
            "avg_steps_success": self._avg(self._success, "steps"),
            "avg_steps_failure": self._avg(self._failure, "steps"),
            "avg_quality_success": self._avg(self._success, "quality"),
            "avg_quality_failure": self._avg(self._failure, "quality"),
            "action_differential": action_diff,
            "recommended": sorted(action_diff.items(), key=lambda x: -x[1])[:3]
        }

    def success_rate(self) -> float:
        total = len(self._success) + len(self._failure)
        return len(self._success) / total if total > 0 else 0.0
