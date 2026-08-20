"""noesis_harness/agent_loop.py

Auto-loop for non-overlapping agents with packed context.

Observe -> pack(budget) -> lease(task) -> act -> judge -> writeback.
Stops on: done, max_turns, loop-guard, judge fail, lease miss, budget miss.

Stdlib. The act() callback is injected — core never calls an LLM.
"""

from __future__ import annotations

import time
from collections.abc import Mapping


class AgentLoop:
    def __init__(self, agent_id, memory, leases, pack, guard, judge,
                 budget=None, hitl=None, events=None, max_turns=8, clock=None):
        if not isinstance(max_turns, int) or isinstance(max_turns, bool) or max_turns < 1:
            raise ValueError("max_turns_invalid")
        if clock is not None and not callable(clock):
            raise ValueError("clock_invalid")
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
        self.clock = clock or time.time

    def _log(self, kind, payload):
        if self.events is not None:
            try:
                self.events.append(kind, payload)
            except Exception:
                return False
        return True

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
            try:
                packed = self.pack.pack(query)
            except Exception as exc:
                self.leases.release(task_key, self.agent_id)
                self._log("pack_error", {"task": task_key, "turn": n, "error": type(exc).__name__})
                return {"status": "pack_error", "reason": type(exc).__name__, "turns": turns, "outputs": outputs}
            if not packed.get("ok"):
                self.leases.release(task_key, self.agent_id)
                return {"status": "context_over", "turns": turns, "outputs": outputs}
            try:
                chk = self.guard.check("%s|%s" % (task_key, query))
            except Exception as exc:
                self.leases.release(task_key, self.agent_id)
                self._log("guard_error", {"task": task_key, "turn": n, "error": type(exc).__name__})
                return {"status": "guard_error", "reason": type(exc).__name__, "turns": turns, "outputs": outputs}
            if not chk.get("ok"):
                self._log("loop_block", {"task": task_key, "turn": n})
                self.leases.release(task_key, self.agent_id)
                return {"status": "loop", "turns": turns, "outputs": outputs}
            ctx = {"turn": n, "query": query, "pack": packed,
                   "agent": self.agent_id, "task": task_key}
            try:
                result = act(ctx) or {}
            except Exception as exc:
                self.leases.release(task_key, self.agent_id)
                self._log("act_error", {"task": task_key, "turn": n, "error": type(exc).__name__})
                return {"status": "act_error", "reason": type(exc).__name__, "turns": turns, "outputs": outputs}
            if not isinstance(result, Mapping):
                self.leases.release(task_key, self.agent_id)
                self._log("result_shape_error", {"task": task_key, "turn": n})
                return {"status": "result_shape_error", "turns": turns, "outputs": outputs}
            out = str(result.get("output") or "")
            outputs.append(out)
            try:
                verdict = self.judge.judge(outputs)
            except Exception as exc:
                self.leases.release(task_key, self.agent_id)
                self._log("judge_error", {"task": task_key, "turn": n, "error": type(exc).__name__})
                return {"status": "judge_error", "reason": type(exc).__name__, "turns": turns, "outputs": outputs}
            if not isinstance(verdict, Mapping):
                self.leases.release(task_key, self.agent_id)
                self._log("judge_shape_error", {"task": task_key, "turn": n})
                return {"status": "judge_shape_error", "turns": turns, "outputs": outputs}
            turn = {"n": n, "output": out, "judge": verdict,
                    "tokens": packed.get("tokens"), "ts": self.clock()}
            turns.append(turn)
            self._log("turn", {"n": n, "agent": self.agent_id, "ok": verdict.get("pass")})
            if result.get("memory"):
                try:
                    self.memory.save(str(result["memory"]), kind="semantic", confidence=0.6)
                except Exception as exc:
                    self.leases.release(task_key, self.agent_id)
                    self._log("memory_error", {"task": task_key, "turn": n, "error": type(exc).__name__})
                    return {"status": "memory_error", "reason": type(exc).__name__, "turns": turns, "outputs": outputs}
            if self.budget is not None:
                key = "%s:%s:%s" % (self.agent_id, task_key, n)
                try:
                    spent = self.budget.spend(key, units=1, validated=bool(verdict.get("pass")))
                except Exception as exc:
                    self.leases.release(task_key, self.agent_id)
                    self._log("budget_error", {"task": task_key, "turn": n, "error": type(exc).__name__})
                    return {"status": "budget_error", "reason": type(exc).__name__, "turns": turns, "outputs": outputs}
                if not spent.get("ok") and spent.get("reason") == "exhausted":
                    self.leases.release(task_key, self.agent_id)
                    return {"status": "budget", "turns": turns, "outputs": outputs}
            if result.get("done") and verdict.get("pass"):
                self.leases.release(task_key, self.agent_id)
                return {"status": "done", "turns": turns, "outputs": outputs}
            if not verdict.get("pass"):
                self.leases.release(task_key, self.agent_id)
                return {"status": "judge_fail", "turns": turns, "outputs": outputs}
            try:
                self.leases.renew(task_key, self.agent_id)
            except Exception as exc:
                self.leases.release(task_key, self.agent_id)
                self._log("lease_renew_error", {"task": task_key, "turn": n, "error": type(exc).__name__})
                return {"status": "lease_renew_error", "reason": type(exc).__name__, "turns": turns, "outputs": outputs}
        self.leases.release(task_key, self.agent_id)
        return {"status": "max_turns", "turns": turns, "outputs": outputs}
