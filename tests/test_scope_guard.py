"""tests/test_scope_guard.py

Unit tests for noesis_harness.scope_guard.ScopeGuard.

Stdlib only. No harness global state is touched by the guard under test.
"""

from __future__ import annotations

import unittest

from noesis_harness.scope_guard import ScopeGuard


class TestScopeGuard(unittest.TestCase):
    def test_enter_sets_current(self):
        with ScopeGuard("alpha") as s:
            self.assertEqual(s.scope, "alpha")
            self.assertEqual(ScopeGuard.current(), "alpha")

    def test_exit_clears_current(self):
        with ScopeGuard("alpha"):
            pass
        self.assertIsNone(ScopeGuard.current())

    def test_current_none_when_idle(self):
        self.assertIsNone(ScopeGuard.current())

    def test_nested_scopes(self):
        with ScopeGuard("outer"):
            self.assertEqual(ScopeGuard.current(), "outer")
            with ScopeGuard("inner") as inner:
                self.assertEqual(ScopeGuard.current(), "inner")
                self.assertEqual(inner.scope, "inner")
            self.assertEqual(ScopeGuard.current(), "outer")
        self.assertIsNone(ScopeGuard.current())

    def test_current_reflects_active(self):
        with ScopeGuard("a"):
            self.assertEqual(ScopeGuard.current(), "a")
            with ScopeGuard("b"):
                self.assertEqual(ScopeGuard.current(), "b")
                with ScopeGuard("c"):
                    self.assertEqual(ScopeGuard.current(), "c")
                self.assertEqual(ScopeGuard.current(), "b")
            self.assertEqual(ScopeGuard.current(), "a")
        self.assertIsNone(ScopeGuard.current())

    def test_reentrant_safe_same_scope(self):
        with ScopeGuard("shared") as outer:
            self.assertEqual(ScopeGuard.current(), "shared")
            with ScopeGuard("shared") as inner:
                self.assertEqual(ScopeGuard.current(), "shared")
                self.assertEqual(ScopeGuard.depth(), 2)
            self.assertEqual(ScopeGuard.current(), "shared")
        self.assertIsNone(ScopeGuard.current())

    def test_depth_tracking(self):
        self.assertEqual(ScopeGuard.depth(), 0)
        with ScopeGuard("x"):
            self.assertEqual(ScopeGuard.depth(), 1)
            with ScopeGuard("y"):
                self.assertEqual(ScopeGuard.depth(), 2)
            self.assertEqual(ScopeGuard.depth(), 1)
        self.assertEqual(ScopeGuard.depth(), 0)

    def test_no_harness_mutation(self):
        import noesis_harness

        before = set(dir(noesis_harness))
        with ScopeGuard("z"):
            pass
        after = set(dir(noesis_harness))
        self.assertEqual(before, after)

    def test_determinism(self):
        first = []
        second = []
        with ScopeGuard("a"):
            first.append(ScopeGuard.current())
            with ScopeGuard("b"):
                first.append(ScopeGuard.current())
            first.append(ScopeGuard.current())
        with ScopeGuard("a"):
            second.append(ScopeGuard.current())
            with ScopeGuard("b"):
                second.append(ScopeGuard.current())
            second.append(ScopeGuard.current())
        self.assertEqual(first, second)
        self.assertIsNone(ScopeGuard.current())

    def test_invalid_scope_rejected(self):
        with self.assertRaises(ValueError):
            ScopeGuard("")
        with self.assertRaises(ValueError):
            ScopeGuard(None)
        with self.assertRaises(ValueError):
            ScopeGuard(123)

    def test_exit_without_enter_raises(self):
        g = ScopeGuard("bad")
        with self.assertRaises(RuntimeError):
            g.__exit__(None, None, None)

    def test_exception_propagates(self):
        with self.assertRaises(ValueError):
            with ScopeGuard("err"):
                raise ValueError("boom")
        self.assertIsNone(ScopeGuard.current())

    def test_reenter_raises(self):
        g = ScopeGuard("dup")
        g.__enter__()
        with self.assertRaises(RuntimeError):
            g.__enter__()
        g.__exit__(None, None, None)


if __name__ == "__main__":
    unittest.main()
