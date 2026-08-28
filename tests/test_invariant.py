"""tests/test_invariant.py

Unit tests for noesis_harness.invariant.check.

Stdlib only. No LLM, no network, no file deletion of sources.
"""

import hashlib
import os
import tempfile
import unittest

from noesis_harness.invariant import check
from noesis_harness.event_store import EventStore


def _write_log(path, records):
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(rec + "\n")


def _sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in fh:
            h.update(chunk)
    return h.hexdigest()


# Rule factories ------------------------------------------------------------

def always_ok(store):
    for _ in store.iter_events():
        pass
    return None


def all_pass_rule():
    return {"name": "always_ok", "fn": always_ok}


def fail_with(detail="violation"):
    def fn(store):
        return detail
    return fn


def seq_monotonic_rule():
    def fn(store):
        last = 0
        for ev in store.iter_events():
            seq = ev.get("seq")
            if isinstance(seq, int) and seq < last:
                return "non-monotonic seq at %r" % (ev,)
            last = seq if isinstance(seq, int) else last
        return None
    return {"name": "seq_monotonic", "fn": fn}


class InvariantTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "events.log")

    def tearDown(self):
        for root, _, files in os.walk(self.tmp):
            for f in files:
                os.remove(os.path.join(root, f))
        os.rmdir(self.tmp)

    def _seed(self, n=3):
        store = EventStore(self.path)
        for i in range(n):
            store.append("tick", {"i": i}, event_id="e%d" % i)

    # 1. all-pass ----------------------------------------------------------
    def test_all_pass(self):
        self._seed()
        result = check(self.path, [all_pass_rule(), seq_monotonic_rule()])
        self.assertTrue(result["passed"])
        self.assertEqual(result["failures"], [])

    # 2. one-fail reported -------------------------------------------------
    def test_one_fail_reported(self):
        self._seed()
        result = check(self.path, [all_pass_rule(), {"name": "always_bad", "fn": fail_with("boom")}])
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["failures"]), 1)
        self.assertEqual(result["failures"][0]["name"], "always_bad")
        self.assertEqual(result["failures"][0]["detail"], "boom")

    # 3. missing file handled ---------------------------------------------
    def test_missing_file_handled(self):
        missing = os.path.join(self.tmp, "does_not_exist.log")
        result = check(missing, [{"name": "x", "fn": fail_with("x")}])
        # Missing file == empty log; a rule that always fails still reports.
        self.assertFalse(result["passed"])
        self.assertEqual(result["failures"][0]["detail"], "x")
        # And a passing rule on a missing file is fine.
        ok = check(missing, [all_pass_rule()])
        self.assertTrue(ok["passed"])

    # 4. fn receives events -----------------------------------------------
    def test_fn_receives_events(self):
        self._seed(2)
        captured = {}

        def fn(store):
            captured["store"] = store
            captured["count"] = sum(1 for _ in store.iter_events())
            return None
        check(self.path, [{"name": "capture", "fn": fn}])
        self.assertIsInstance(captured["store"], EventStore)
        self.assertEqual(captured["count"], 2)

    # 5. determinism -------------------------------------------------------
    def test_determinism(self):
        self._seed()
        rules = [all_pass_rule(), seq_monotonic_rule(), {"name": "c", "fn": fail_with("c")}] * 3
        first = check(self.path, rules)
        second = check(self.path, rules)
        self.assertEqual(first, second)

    # 6. empty log ---------------------------------------------------------
    def test_empty_log(self):
        result = check(self.path, [all_pass_rule()])
        self.assertTrue(result["passed"])
        self.assertEqual(result["failures"], [])

    # 7. multiple rules ----------------------------------------------------
    def test_multiple_rules_collect_all_failures(self):
        self._seed()
        rules = [
            {"name": "r1", "fn": fail_with("a")},
            {"name": "r2", "fn": always_ok},
            {"name": "r3", "fn": fail_with("b")},
        ]
        result = check(self.path, rules)
        self.assertFalse(result["passed"])
        names = [f["name"] for f in result["failures"]]
        self.assertEqual(names, ["r1", "r3"])

    # 8. no mutation -------------------------------------------------------
    def test_no_mutation_of_log(self):
        self._seed(4)
        before = _sha1(self.path)
        check(self.path, [all_pass_rule(), seq_monotonic_rule()])
        after = _sha1(self.path)
        self.assertEqual(before, after)

    # 9. rule can flag real invariant violation ----------------------------
    def test_rule_flags_out_of_order_seq(self):
        out_of_order = [
            '{"event_id":"a","type":"x","payload":1,"seq":1}',
            '{"event_id":"b","type":"x","payload":2,"seq":5}',
            '{"event_id":"c","type":"x","payload":3,"seq":2}',
        ]
        _write_log(self.path, out_of_order)
        result = check(self.path, [seq_monotonic_rule()])
        self.assertFalse(result["passed"])
        self.assertIn("non-monotonic", result["failures"][0]["detail"])

    # 10. rule passes well-ordered seq ------------------------------------
    def test_rule_passes_ordered_seq(self):
        ordered = [
            '{"event_id":"a","type":"x","payload":1,"seq":1}',
            '{"event_id":"b","type":"x","payload":2,"seq":2}',
            '{"event_id":"c","type":"x","payload":3,"seq":3}',
        ]
        _write_log(self.path, ordered)
        result = check(self.path, [seq_monotonic_rule()])
        self.assertTrue(result["passed"])

    # 11. unnamed / fn-less rules ignored safely --------------------------
    def test_missing_fn_ignored(self):
        self._seed()
        rules = [{"name": "no-fn"}, {"name": "ok", "fn": all_pass_rule()["fn"]}]
        result = check(self.path, rules)
        self.assertTrue(result["passed"])

    # 12. empty rules list -------------------------------------------------
    def test_empty_rules(self):
        self._seed()
        result = check(self.path, [])
        self.assertTrue(result["passed"])
        self.assertEqual(result["failures"], [])


if __name__ == "__main__":
    unittest.main()
