"""Tests for the allowlist proxy jail (Phase A model_task enforcement)."""
import http.server
import socket
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from noesis_harness.proxy_jail import AllowlistProxy, ProxyJailError


def _no_system_bypass():
    return patch("urllib.request.proxy_bypass", return_value=False)


class _StubHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"upstream-ok"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def _free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class _Upstream:
    def __init__(self):
        self.port = _free_port()
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", self.port), _StubHandler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


class AllowlistProxyTests(unittest.TestCase):
    def setUp(self):
        self.upstream = _Upstream()

    def tearDown(self):
        self.upstream.stop()

    def test_allowed_host_forwarded(self):
        with AllowlistProxy({"127.0.0.1"}) as proxy:
            with _no_system_bypass():
                handler = urllib.request.ProxyHandler({"http": "http://" + proxy.address})
                opener = urllib.request.build_opener(handler)
                response = opener.open("http://127.0.0.1:%d/ok" % self.upstream.port, timeout=10)
                self.assertEqual(response.read(), b"upstream-ok")
            self.assertEqual(proxy.allowed_count, 1)
            self.assertEqual(proxy.blocked_count, 0)

    def test_disallowed_host_rejected_fail_closed(self):
        with AllowlistProxy({"example.com"}) as proxy:
            with _no_system_bypass():
                handler = urllib.request.ProxyHandler({"http": "http://" + proxy.address})
                opener = urllib.request.build_opener(handler)
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    opener.open("http://127.0.0.1:%d/ok" % self.upstream.port, timeout=10)
            self.assertEqual(caught.exception.code, 403)
            self.assertGreaterEqual(proxy.blocked_count, 1)

    def test_empty_allowlist_rejected_at_construction(self):
        with self.assertRaises(ProxyJailError):
            AllowlistProxy([])

    def test_invalid_host_rejected(self):
        with self.assertRaises(ProxyJailError):
            AllowlistProxy({"bad/host"})
        with self.assertRaises(ProxyJailError):
            AllowlistProxy({"user@host"})

    def test_connect_denied_for_non_allowlisted_authority(self):
        with AllowlistProxy({"example.com"}) as proxy:
            host, port_text = proxy.address.split(":")
            client = socket.create_connection((host, int(port_text)), timeout=10)
            client.sendall(b"CONNECT evil.example.net:443 HTTP/1.1\r\nHost: evil.example.net:443\r\n\r\n")
            response = client.recv(4096).decode("latin-1")
            client.close()
            self.assertTrue(response.startswith("HTTP/1.1 403"), response)

    def test_env_overrides_shape(self):
        with AllowlistProxy({"api.example.test"}) as proxy:
            env = proxy.env_overrides()
            for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
                self.assertTrue(env[key].startswith("http://127.0.0.1:"))
            self.assertEqual(env["NO_PROXY"], "")


if __name__ == "__main__":
    unittest.main()
