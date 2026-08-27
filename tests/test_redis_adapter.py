"""tests/test_redis_adapter.py

Tests for the optional Redis cache adapter addon. The adapter must never raise
when `redis` is absent and must report status "disabled" so callers can branch
without try/except.

These tests force `redis` to be unimportable so the disabled path is exercised
deterministically even if `redis` happens to be installed in the environment.
"""

from __future__ import annotations

import contextlib
import sys
import types
import unittest
from unittest import mock

import addons.redis_adapter as ra


class _FakeMissingRedis(types.ModuleType):
    """A `redis` module stand-in that raises on attribute access / import."""

    def __getattr__(self, name):
        raise ImportError("redis is a fictional missing module in this test")


@contextlib.contextmanager
def _with_redis_missing():
    """Context manager that makes `import redis` fail, then restores state."""
    saved = sys.modules.get("redis")

    class _Block(types.ModuleType):
        def __getattr__(self, _name):
            raise ImportError("forced: redis not installed")

    blocker = _Block("redis")
    sys.modules["redis"] = blocker
    try:
        yield
    finally:
        if saved is None:
            sys.modules.pop("redis", None)
        else:
            sys.modules["redis"] = saved


class RedisAdapterDisabledTests(unittest.TestCase):
    def test_import_does_not_require_redis(self):
        # The module imported at top of file without redis present.
        self.assertTrue(hasattr(ra, "RedisAdapter"))
        self.assertTrue(hasattr(ra, "ping"))

    def test_module_ping_disabled(self):
        with _with_redis_missing():
            result = ra.ping()
        self.assertEqual(result["status"], "disabled")
        self.assertFalse(result.get("hit", True))

    def test_module_get_disabled(self):
        with _with_redis_missing():
            result = ra.get("missing-key")
        self.assertEqual(result["status"], "disabled")

    def test_module_set_disabled(self):
        with _with_redis_missing():
            result = ra.set("k", "v", ttl=10)
        self.assertEqual(result["status"], "disabled")
        self.assertIsNone(result.get("stored"))

    def test_class_ping_get_set_disabled(self):
        with _with_redis_missing():
            adapter = ra.RedisAdapter(host="localhost", port=6379)
            self.assertEqual(adapter.ping()["status"], "disabled")
            self.assertEqual(adapter.get("x")["status"], "disabled")
            self.assertEqual(adapter.set("x", 1)["status"], "disabled")

    def test_no_raise_when_redis_missing(self):
        with _with_redis_missing():
            for fn in (ra.ping, lambda: ra.get("a"), lambda: ra.set("a", 1)):
                try:
                    fn()
                except Exception as exc:  # pragma: no cover
                    self.fail("operation raised on missing redis: %r" % exc)

    def test_default_ttl_accepted_without_backend(self):
        with _with_redis_missing():
            adapter = ra.RedisAdapter(default_ttl=60)
            self.assertEqual(adapter.set("k", "v")["status"], "disabled")

    def test_result_shape_has_status_key(self):
        with _with_redis_missing():
            for result in (ra.ping(), ra.get("a"), ra.set("a", 1)):
                self.assertIn("status", result)
                self.assertIsInstance(result["status"], str)


if __name__ == "__main__":
    unittest.main()
