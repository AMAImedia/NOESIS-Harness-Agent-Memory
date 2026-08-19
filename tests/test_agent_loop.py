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
    def pack(self, query):
        return {"ok": True, "tokens": 4}


class _Guard:
    def __init__(self, ok=True):
        self.ok = ok

    def check(self, action):
        return {"ok": self.ok}


class _Judge:
    def judge(self, outputs):
        return {"pass": True}


class AgentLoopTests(unittest.TestCase):
    def make_loop(self, leases=None, guard=None, max_turns=2):
        return AgentLoop("agent", _Memory(), leases or _Leases(), _Pack(), guard or _Guard(), _Judge(), max_turns=max_turns)

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

    def test_done_requires_passing_judge(self):
        loop = self.make_loop(max_turns=3)
        result = loop.run("task", "query", lambda context: {"done": True, "output": "accepted"})
        self.assertEqual(result["status"], "done")
        self.assertEqual(len(result["outputs"]), 1)


if __name__ == "__main__":
    unittest.main()
