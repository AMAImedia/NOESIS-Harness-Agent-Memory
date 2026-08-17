import json
import threading
import unittest
import urllib.error
import urllib.request

from noesis_harness.health_server import HealthServer


class ControlPlaneUITests(unittest.TestCase):
    def test_ui_is_self_contained_read_only_surface(self):
        with HealthServer(port=0) as server:
            url = "http://%s:%d/ui" % server.address
            request = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(request, timeout=2) as response:
                body = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn("Content-Security-Policy", response.headers)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertIn("/health", body)
            self.assertIn("/models", body)
            self.assertIn("Sessions", body)
            self.assertIn("No session mutation endpoint", body)
            self.assertNotIn("OPENAI_API_KEY", body)
            self.assertNotIn("Authorization", body)

    def test_ui_root_alias_and_post_denial(self):
        with HealthServer(port=0) as server:
            root = "http://%s:%d/" % server.address
            with urllib.request.urlopen(root, timeout=2) as response:
                self.assertEqual(response.status, 200)
                self.assertIn("text/html", response.headers["Content-Type"])
            try:
                urllib.request.urlopen(urllib.request.Request(root, method="POST", data=b"{}"), timeout=2)
            except urllib.error.HTTPError as error:
                self.assertEqual(error.code, 405)
                payload = json.loads(error.read().decode("utf-8"))
                self.assertEqual(payload["status"], "denied")
            else:
                self.fail("POST / must remain denied")


if __name__ == "__main__":
    unittest.main()
