import json
import unittest
import urllib.error
import urllib.request

from noesis_harness.health_server import HealthServer


TOKEN = "local-test-token-1234567890"


class HealthAuthTests(unittest.TestCase):
    def test_non_loopback_requires_explicit_security_configuration(self):
        with self.assertRaises(ValueError):
            HealthServer(host="0.0.0.0")
        with self.assertRaises(ValueError):
            HealthServer(host="0.0.0.0", allow_non_loopback=True, acknowledge_lan_warning=True)
        with self.assertRaises(ValueError):
            HealthServer(host="0.0.0.0", allow_non_loopback=True, auth_token="short", acknowledge_lan_warning=True)
        with self.assertRaises(ValueError):
            HealthServer(host="0.0.0.0", allow_non_loopback=True, auth_token=TOKEN)

    def test_lan_adapter_authenticates_without_leaking_token(self):
        with HealthServer(host="0.0.0.0", port=0, allow_non_loopback=True, auth_token=TOKEN, acknowledge_lan_warning=True) as server:
            url = "http://127.0.0.1:%d/health" % server.address[1]
            for header in ({}, {"Authorization": "Bearer wrong-token"}):
                for suffix in ("", "/api/operator/snapshot?task_id=task-1&receipt_id=receipt-1", "/api/telemetry/events?task_id=task-1"):
                    request = urllib.request.Request(url + suffix, headers=header, method="GET")
                    try:
                        urllib.request.urlopen(request, timeout=2)
                    except urllib.error.HTTPError as error:
                        self.assertEqual(error.code, 401)
                        payload = error.read().decode("utf-8")
                        error.close()
                        self.assertNotIn(TOKEN, payload)
                        self.assertEqual(json.loads(payload)["error"]["code"], "authentication_required")
                    else:
                        self.fail("unauthenticated LAN request must be rejected")
            request = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOKEN}, method="GET")
            with urllib.request.urlopen(request, timeout=2) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["X-NOESIS-Network-Warning"], "authenticated non-loopback adapter; do not expose to untrusted networks")
                self.assertNotIn(TOKEN, response.headers["X-NOESIS-Network-Warning"])

    def test_loopback_remains_unauthenticated_by_default(self):
        with HealthServer(port=0) as server:
            request = urllib.request.Request("http://%s:%d/health" % server.address, method="GET")
            with urllib.request.urlopen(request, timeout=2) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["X-NOESIS-Network-Warning"], "loopback-only")


if __name__ == "__main__":
    unittest.main()
