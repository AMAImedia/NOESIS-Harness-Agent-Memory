import unittest

from noesis_harness.agent_loop import AgentLoop


class _Memory:
    def __init__(self):
        self.saved = []

    def save(self, value, kind, confidence):
        self.saved.append((value, kind, confidence))


class _Leases:
    def __init__(self, acquire_ok=True):
        self.acquire_ok = acquire_ok
        self.acquired = 0
        self.released = 0
        self.renewed = 0

    def acquire(self, task_key, agent_id):
        self.acquired += 1
        return {"ok": self.acquire_ok, "holder": None if self.acquire_ok else "other-agent"}

    def release(self, task_key, agent_id):
        self.released += 1

    def renew(self, task_key, agent_id):
        self.renewed += 1


class _Pack:
    def __init__(self, ok=True):
        self.ok = ok

    def pack(self, query):
        return {"ok": self.ok, "tokens": 4}


class _Guard:
    def __init__(self, ok=True):
        self.ok = ok

    def check(self, action):
        return {"ok": self.ok}


class _Judge:
    def __init__(self, ok=True):
        self.ok = ok

    def judge(self, outputs):
        if not self.ok:
            raise RuntimeError("judge failure")
        return {"pass": True}


class AgentLoopTests(unittest.TestCase):
    def make_loop(self, leases=None, guard=None, max_turns=2, pack=None, judge=None, clock=None):
        return AgentLoop("agent", _Memory(), leases or _Leases(), pack or _Pack(), guard or _Guard(), judge or _Judge(), max_turns=max_turns, clock=clock)

    def test_max_turns_is_bounded(self):
        calls = []
        loop = self.make_loop(max_turns=2)
        result = loop.run("task", "query", lambda context: calls.append(context["turn"]) or {"output": "ok"})
        self.assertEqual(result["status"], "max_turns")
        self.assertEqual(calls, [1, 2])
        self.assertEqual(len(result["turns"]), 2)

    def test_lease_miss_prevents_action(self):
        calls = []
        leases = _Leases(acquire_ok=False)
        result = self.make_loop(leases=leases).run("task", "query", lambda context: calls.append(context) or {"done": True})
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(calls, [])
        self.assertEqual(leases.released, 0)

    def test_loop_guard_stops_before_action(self):
        calls = []
        result = self.make_loop(guard=_Guard(ok=False)).run("task", "query", lambda context: calls.append(context) or {"done": True})
        self.assertEqual(result["status"], "loop")
        self.assertEqual(calls, [])

    def test_context_failure_releases_lease(self):
        leases = _Leases()
        result = self.make_loop(leases=leases, pack=_Pack(ok=False)).run("task", "query", lambda context: {"done": True})
        self.assertEqual(result["status"], "context_over")
        self.assertEqual(leases.released, 1)

    def test_action_exception_releases_lease(self):
        leases = _Leases()
        result = self.make_loop(leases=leases).run("task", "query", lambda context: (_ for _ in ()).throw(ValueError("bad action")))
        self.assertEqual(result["status"], "act_error")
        self.assertEqual(result["reason"], "ValueError")
        self.assertEqual(leases.released, 1)

    def test_judge_exception_releases_lease(self):
        leases = _Leases()
        result = self.make_loop(leases=leases, judge=_Judge(ok=False)).run("task", "query", lambda context: {"output": "candidate"})
        self.assertEqual(result["status"], "judge_error")
        self.assertEqual(result["reason"], "RuntimeError")
        self.assertEqual(leases.released, 1)

    def test_clock_is_injected_for_deterministic_turn_receipts(self):
        loop = self.make_loop(max_turns=1, clock=lambda: 123.0)
        result = loop.run("task", "query", lambda context: {"done": True, "output": "accepted"})
        self.assertEqual(result["turns"][0]["ts"], 123.0)

    def test_done_requires_passing_judge(self):
        loop = self.make_loop(max_turns=3)
        result = loop.run("task", "query", lambda context: {"done": True, "output": "accepted"})
        self.assertEqual(result["status"], "done")
        self.assertEqual(len(result["outputs"]), 1)


if __name__ == "__main__":
    unittest.main()
