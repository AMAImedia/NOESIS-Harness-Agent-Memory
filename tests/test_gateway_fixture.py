import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from noesis_harness.bridge_discovery import BridgeCandidate, BridgeDiscovery
from noesis_harness.gateway_fixture import GatewayFixture, GatewayFixtureError


class GatewayFixtureTests(unittest.TestCase):
    def test_hermes_fixture_auth_and_discovery(self):
        with tempfile.TemporaryDirectory() as root:
            audit = str(Path(root, "hermes-audit.jsonl"))
            with GatewayFixture("hermes_webui", token="fixture-token-123456", audit_path=audit, models=({"provider": "hermes_webui", "id": "hermes-model"},)) as fixture:
                base = "http://%s:%d" % fixture.address
                candidate = BridgeCandidate("hermes-fixture", "hermes_webui", base)
                unauth = urllib.request.Request(base + "/health", method="GET")
                with self.assertRaises(urllib.error.HTTPError) as context:
                    urllib.request.urlopen(unauth, timeout=2)
                self.assertEqual(context.exception.code, 401)
                status = BridgeDiscovery((candidate,)).probe(candidate)
                self.assertEqual(status.status, "unavailable")
                auth = {"Authorization": "Bearer fixture-token-123456", "X-NOESIS-Agent": "agent-a"}
                models = urllib.request.Request(base + "/models", headers=auth, method="GET")
                with urllib.request.urlopen(models, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn("hermes-model", response.read().decode("utf-8"))
            events = tuple(json.loads(line) for line in Path(audit).read_text(encoding="utf-8").splitlines())
            self.assertGreaterEqual(len(events), 2)
            self.assertTrue(all("fixture-token-123456" not in json.dumps(event) for event in events))

    def test_deepseek_fixture_is_ready_and_metadata_only(self):
        with GatewayFixture("deepseek_harness", models=({"provider": "deepseek_harness", "id": "dsh-model", "capabilities": {"tools": False}},)) as fixture:
            candidate = BridgeCandidate("dsh-fixture", "deepseek_harness", "http://%s:%d" % fixture.address)
            status = BridgeDiscovery((candidate,)).probe(candidate)
            self.assertEqual(status.status, "ready")
            self.assertEqual(status.model_count, 1)

    def test_audit_does_not_cross_agent_leak(self):
        with tempfile.TemporaryDirectory() as root:
            audit = str(Path(root, "audit.jsonl"))
            with GatewayFixture("hermes_webui", audit_path=audit) as fixture:
                url = "http://%s:%d/health" % fixture.address
                for agent in ("agent-a", "agent-b"):
                    request = urllib.request.Request(url, headers={"X-NOESIS-Agent": agent}, method="GET")
                    with urllib.request.urlopen(request, timeout=2):
                        pass
            events = tuple(json.loads(line) for line in Path(audit).read_text(encoding="utf-8").splitlines())
            self.assertEqual([event["agent_id"] for event in events], ["agent-a", "agent-b"])
            for event in events:
                self.assertNotIn("payload", event)
                self.assertNotIn("prompt", event)

    def test_invalid_fixture_token_fails_closed(self):
        with self.assertRaises(GatewayFixtureError):
            GatewayFixture("deepseek_harness", token="short")


if __name__ == "__main__":
    unittest.main()
