"""noesis_harness/procedures.py

Procedural memory runner: match stored workflows to a context, then execute.

Pattern adapted from agentmemory procedural tier + Hermes skill triggers.
Stored facts look like: 'when <trigger> then <action>'.
Stdlib only. Execution is a user callback — the core never calls an LLM.
"""

from __future__ import annotations

import re


_SPLIT = re.compile(r"(?i)\bthen\b|->")


def parse_procedure(fact):
    parts = _SPLIT.split(fact, maxsplit=1)
    if len(parts) != 2:
        return None
    trigger, action = parts[0].strip(), parts[1].strip()
    if trigger.lower().startswith("when "):
        trigger = trigger[5:].strip()
    if not trigger or not action:
        return None
    return {"trigger": trigger, "action": action, "fact": fact}


def _tokens(text):
    return set(re.findall(r"[a-z0-9]{3,}", (text or "").lower()))


def overlap(trigger, context):
    a, b = _tokens(trigger), _tokens(context)
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a))


class ProcedureRunner:
    """Match procedural memories against context; optionally fire a callback."""

    def __init__(self, memory, min_overlap=0.5):
        self.memory = memory
        self.min_overlap = min_overlap

    def match(self, context, limit=5):
        hits = []
        for row in self.memory.profile(kind="procedural", limit=50):
            parsed = parse_procedure(row.get("fact", ""))
            if not parsed:
                continue
            score = overlap(parsed["trigger"], context)
            if score >= self.min_overlap:
                item = dict(row)
                item.update(parsed)
                item["score"] = score
                hits.append(item)
        hits.sort(key=lambda x: (-x["score"], -x.get("strength", 0)))
        return hits[:limit]

    def run(self, context, execute=None, limit=1):
        matched = self.match(context, limit=limit)
        results = []
        for item in matched:
            out = {"procedure": item, "ok": True, "result": None}
            if execute is not None:
                try:
                    out["result"] = execute(item["action"], item)
                except Exception as exc:
                    out["ok"] = False
                    out["result"] = str(exc)
            results.append(out)
        return results
