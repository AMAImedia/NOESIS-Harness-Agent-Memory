"""noesis_harness/scope.py

Fail-closed tenant prefix on Memory facts. Isolated unless kind=shared.
"""

from __future__ import annotations


class ScopedMemory:
    def __init__(self, memory, agent_id):
        if not agent_id:
            raise ValueError("agent_id required")
        self.memory = memory
        self.agent_id = str(agent_id)
        self.prefix = "scope:%s|" % self.agent_id

    def save(self, fact, kind="semantic", confidence=0.5):
        if kind == "shared":
            return self.memory.save(fact, kind="semantic", confidence=confidence)
        return self.memory.save(self.prefix + fact, kind=kind, confidence=confidence)

    def recall(self, query, limit=10, kind=""):
        hits = self.memory.recall(query, limit=limit * 3, kind=kind)
        mine = []
        for h in hits:
            fact = h.get("fact") or ""
            if fact.startswith(self.prefix):
                item = dict(h)
                item["fact"] = fact[len(self.prefix):]
                mine.append(item)
            elif fact.startswith("scope:"):
                continue
            else:
                mine.append(h)
            if len(mine) >= limit:
                break
        return mine
