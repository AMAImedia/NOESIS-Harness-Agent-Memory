"""tests/test_webhook_sink.py

Tests for addons/webhook_sink.py. The sink is disabled by default; these tests
never perform network I/O and never require `requests` to be installed.
"""

import unittest
from unittest import mock

from addons import webhook_sink


class TestWebhookSinkDisabled(unittest.TestCase):
    def test_disabled_by_default_returns_status_disabled(self):
        result = webhook_sink.send("https://example.test/hook", {"a": 1})
        self.assertEqual(result["status"], "disabled")

    def test_disabled_flag_is_false(self):
        self.assertIs(webhook_sink.ENABLED, False)

    def test_disabled_does_not_deliver(self):
        result = webhook_sink.send("https://example.test/hook", {"a": 1})
        self.assertFalse(result.get("delivered", True))

    def test_disabled_gives_reason(self):
        result = webhook_sink.send("https://example.test/hook", {"a": 1})
        self.assertIn("reason", result)
        self.assertIsInstance(result["reason"], str)
        self.assertTrue(result["reason"])


class TestWebhookSinkNoNetwork(unittest.TestCase):
    def test_importing_module_never_requires_requests(self):
        import importlib

        importlib.reload(webhook_sink)
        self.assertFalse(hasattr(webhook_sink, "requests"))

    def test_send_without_requests_available_returns_disabled(self):
        saved = webhook_sink.ENABLED
        webhook_sink.ENABLED = True
        try:
            real_import = __import__

            def blocked_import(name, *args, **kwargs):
                if name == "requests" or name.startswith("requests."):
                    raise ImportError("blocked for test")
                return real_import(name, *args, **kwargs)

            with mock.patch("builtins.__import__", side_effect=blocked_import):
                result = webhook_sink.send("https://example.test/hook", {"x": 1})
            self.assertEqual(result["status"], "disabled")
            self.assertIn("reason", result)
        finally:
            webhook_sink.ENABLED = saved

    def test_send_never_raises_when_disabled(self):
        # Even with a junk url and payload, disabled mode must not raise.
        for url in ["", None, "not a url", "https://example.test/hook"]:
            for payload in [None, {}, "payload", 123]:
                result = webhook_sink.send(url, payload)  # type: ignore
                self.assertEqual(result["status"], "disabled")


class TestWebhookSinkEnabledMocked(unittest.TestCase):
    def setUp(self):
        self.saved = webhook_sink.ENABLED
        webhook_sink.ENABLED = True

    def tearDown(self):
        webhook_sink.ENABLED = self.saved

    def test_enabled_with_mocked_requests_posts_and_returns_ok(self):
        fake_resp = mock.Mock()
        fake_resp.status_code = 204
        fake_post = mock.Mock(return_value=fake_resp)

        fake_requests = mock.Mock()
        fake_requests.post = fake_post

        with mock.patch.dict("sys.modules", {"requests": fake_requests}):
            result = webhook_sink.send("https://example.test/hook", {"k": "v"})

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["delivered"])
        self.assertEqual(result["status_code"], 204)
        fake_post.assert_called_once()
        args, kwargs = fake_post.call_args
        self.assertEqual(args[0], "https://example.test/hook")
        self.assertEqual(kwargs["json"], {"k": "v"})

    def test_enabled_post_failure_returns_error_not_raise(self):
        fake_requests = mock.Mock()
        fake_requests.post = mock.Mock(side_effect=RuntimeError("boom"))

        with mock.patch.dict("sys.modules", {"requests": fake_requests}):
            result = webhook_sink.send("https://example.test/hook", {"k": "v"})

        self.assertEqual(result["status"], "error")
        self.assertFalse(result["delivered"])
        self.assertIn("reason", result)


if __name__ == "__main__":
    unittest.main()
