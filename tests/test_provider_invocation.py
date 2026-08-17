import json
import unittest

from noesis_harness.provider_invocation import (
    InvocationRequest,
    OpenAICompatibleInvocationAdapter,
    ProviderInvocationError,
)


class ProviderInvocationTests(unittest.TestCase):
    def _transport(self, request, timeout):
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.full_url, "http://127.0.0.1:9000/v1/chat/completions")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "deepseek-local")
        return 200, json.dumps({"id": "resp-1", "choices": [{"message": {"content": "data only"}}]}).encode()

    def test_explicit_invocation_and_credential_resolver(self):
        calls = []
        adapter = OpenAICompatibleInvocationAdapter(
            "deepseek-1", "http://127.0.0.1:9000", "deepseek-local",
            {"streaming": True, "tools": True}, auth_mode="bearer_ref",
            credential_ref="DEEPSEEK_TOKEN", credential_resolver=lambda ref: calls.append(ref) or "token-value",
            transport=self._transport,
        )
        result = adapter.invoke(InvocationRequest("sess-1", "task-1", "deepseek-local", ({"role": "user", "content": "hello"},), ("streaming",)))
        self.assertEqual(result.status, "ready")
        self.assertEqual(result.request_id, "resp-1")
        self.assertEqual(calls, ["DEEPSEEK_TOKEN"])

    def test_missing_capability_fails_closed(self):
        adapter = OpenAICompatibleInvocationAdapter("p", "http://127.0.0.1:9000", "m", {"streaming": False}, transport=self._transport)
        with self.assertRaises(ProviderInvocationError):
            adapter.invoke(InvocationRequest("s", "t", "m", ({"role": "user", "content": "x"},), ("tools",)))

    def test_model_is_pinned_and_request_is_bounded(self):
        adapter = OpenAICompatibleInvocationAdapter("p", "http://127.0.0.1:9000", "m", {}, transport=self._transport)
        with self.assertRaises(ProviderInvocationError):
            adapter.invoke(InvocationRequest("s", "t", "other", ({"role": "user", "content": "x"},)))
        with self.assertRaises(ProviderInvocationError):
            adapter.invoke(InvocationRequest("s", "t", "m", ({"role": "user", "content": "x" * 300000},)))

    def test_interrupted_provider_timeout_fails_closed(self):
        def interrupted_transport(request, timeout):
            raise TimeoutError("provider response interrupted")

        adapter = OpenAICompatibleInvocationAdapter("p", "http://127.0.0.1:9000", "m", {}, transport=interrupted_transport)
        with self.assertRaisesRegex(ProviderInvocationError, "provider_timeout"):
            adapter.invoke(InvocationRequest("s", "t", "m", ({"role": "user", "content": "x"},)))

    def test_partial_provider_body_is_rejected_without_side_effect(self):
        def partial_transport(request, timeout):
            return 200, b'{"id":"partial","choices":['

        adapter = OpenAICompatibleInvocationAdapter("p", "http://127.0.0.1:9000", "m", {}, transport=partial_transport)
        with self.assertRaisesRegex(ProviderInvocationError, "provider_invalid_json"):
            adapter.invoke(InvocationRequest("s", "t", "m", ({"role": "user", "content": "x"},)))


if __name__ == "__main__":
    unittest.main()
