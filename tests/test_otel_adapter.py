"""tests/test_otel_adapter.py

Tests for the optional, disabled-by-default OpenTelemetry adapter.

These run WITHOUT opentelemetry installed. They assert that importing the
module is safe, that every function degrades to a clear "disabled" dict, and
that no code path raises when the backend is absent.
"""

import unittest

from addons import otel_adapter


class TestOtelAdapterDisabled(unittest.TestCase):
    def test_module_imports_without_otel(self):
        # Importing the module must not require opentelemetry.
        self.assertTrue(hasattr(otel_adapter, "emit"))
        self.assertTrue(hasattr(otel_adapter, "span"))

    def test_emit_returns_disabled_dict(self):
        result = otel_adapter.emit("invocations", 1.0, {"agent": "x"})
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "disabled")
        self.assertFalse(result["recorded"])

    def test_emit_no_crash_without_value(self):
        # A non-float value should not crash; it is coerced defensively only
        # when otel is present. Without otel it returns disabled regardless.
        result = otel_adapter.emit("invocations", 3, None)
        self.assertEqual(result["status"], "disabled")

    def test_span_yields_disabled_dict(self):
        with otel_adapter.span("do_work", {"k": "v"}) as meta:
            self.assertIsInstance(meta, dict)
            self.assertEqual(meta["status"], "disabled")
            self.assertFalse(meta["recorded"])

    def test_span_block_runs_when_disabled(self):
        ran = []
        with otel_adapter.span("do_work") as meta:
            ran.append(1)
        self.assertEqual(ran, [1])
        self.assertEqual(meta["status"], "disabled")

    def test_no_exception_on_missing_otel(self):
        # The pure guard must never raise for either API.
        try:
            otel_adapter.emit("m", 1.0)
            with otel_adapter.span("s"):
                pass
        except Exception as exc:  # pragma: no cover - guard contract
            self.fail("otel_adapter raised without opentelemetry: %r" % exc)


if __name__ == "__main__":
    unittest.main()
