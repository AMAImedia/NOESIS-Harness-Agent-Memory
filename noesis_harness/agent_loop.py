"""noesis_harness/agent_loop.py

Auto-loop for non-overlapping agents with packed context.

Observe -> pack(budget) -> lease(task) -> act -> judge -> writeback.
Stops on: done, max_turns, loop-guard, judge fail, lease miss, budget miss.

Stdlib. The act() callback is injected — core never calls an LLM.
"""

from __future__ import annotations

import time


class AgentLoop:
    def __init__(self, agent_id, memory, leases, pack, guard, judge,
                 budget=None, hitl=None, events=None, max_turns=8):
        self.agent_id = agent_id
        self.memory = memory
        self.leases = leases
        self.pack = pack
        self.guard = guard
        self.judge = judge
        self.budget = budget
        self.hitl = hitl
        self.events = events
        self.max_turns = max_turns

    def _log(self, kind, payload):
        if self.events is not None:
            self.events.append(kind, payload)

    def run(self, task_key, query, act):
        """act(ctx) -> {done, output, memory?}  Never called without a lease."""
        outputs = []
        turns = []
        for n in range(1, self.max_turns + 1):
            claim = self.leases.acquire(task_key, self.agent_id)
            if not claim.get("ok"):
                self._log("lease_miss", {"task": task_key, "holder": claim.get("holder")})
                return {"status": "blocked", "holder": claim.get("holder"),
                        "turns": turns, "outputs": outputs}
            packed = self.pack.pack(query)
            if not packed.get("ok"):
                return {"status": "context_over", "turns": turns, "outputs": outputs}
            chk = self.guard.check("%s|%s" % (task_key, query))
            if not chk.get("ok"):
                self._log("loop_block", {"task": task_key, "turn": n})
                return {"status": "loop", "turns": turns, "outputs": outputs}
            ctx = {"turn": n, "query": query, "pack": packed,
                   "agent": self.agent_id, "task": task_key}
            result = act(ctx) or {}
            out = str(result.get("output") or "")
            outputs.append(out)
            verdict = self.judge.judge(outputs)
            turn = {"n": n, "output": out, "judge": verdict,
                    "tokens": packed.get("tokens"), "ts": time.time()}
            turns.append(turn)
            self._log("turn", {"n": n, "agent": self.agent_id, "ok": verdict.get("pass")})
            if result.get("memory"):
                self.memory.save(str(result["memory"]), kind="semantic", confidence=0.6)
            if self.budget is not None:
                key = "%s:%s:%s" % (self.agent_id, task_key, n)
                spent = self.budget.spend(key, units=1, validated=bool(verdict.get("pass")))
                if not spent.get("ok") and spent.get("reason") == "exhausted":
                    self.leases.release(task_key, self.agent_id)
                    return {"status": "budget", "turns": turns, "outputs": outputs}
            if result.get("done") and verdict.get("pass"):
                self.leases.release(task_key, self.agent_id)
                return {"status": "done", "turns": turns, "outputs": outputs}
            if not verdict.get("pass"):
                self.leases.release(task_key, self.agent_id)
                return {"status": "judge_fail", "turns": turns, "outputs": outputs}
            self.leases.renew(task_key, self.agent_id)
        self.leases.release(task_key, self.agent_id)
        return {"status": "max_turns", "turns": turns, "outputs": outputs}
