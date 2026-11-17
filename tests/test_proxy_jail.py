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


class AllowlistProxyHardeningTests(unittest.TestCase):
    """Protocol-level evasion coverage: canonicalization, strict CONNECT
    parsing, split-brain HTTP, and header caps."""

    def setUp(self):
        self.upstream = _Upstream()

    def tearDown(self):
        self.upstream.stop()

    def _open(self, proxy):
        host, port_text = proxy.address.split(":")
        return socket.create_connection((host, int(port_text)), timeout=10)

    def _raw(self, proxy, payload, expect_status):
        client = self._open(proxy)
        client.sendall(payload)
        try:
            client.settimeout(10)
            response = client.recv(4096).decode("latin-1")
        finally:
            client.close()
        self.assertTrue(response.startswith(expect_status), response)
        return response

    def test_allowlist_canonicalization_variants(self):
        proxy = AllowlistProxy({"EXAMPLE.com.", "example.com.", "Example.COM", "example.com "})
        self.assertEqual(proxy.allowed_hosts, frozenset({"example.com"}))
        for variant in ("EXAMPLE.com.", "example.com.", "Example.COM", "example.com"):
            self.assertTrue(proxy._is_allowed(variant), variant)
        self.assertFalse(proxy._is_allowed("evil.example.com"))
        self.assertFalse(proxy._is_allowed("example.com.evil"))
        self.assertFalse(proxy._is_allowed("example.com:443"))

    def test_allowlist_rejects_embedded_dotdot_nul_whitespace(self):
        for bad in ("evil..com", "exa mple.com", "exa\tmple.com", "exa\x00mple.com", "evil./com"):
            with self.assertRaises(ProxyJailError):
                AllowlistProxy({bad})

    def test_connect_malformed_authorities_rejected_400(self):
        malformed = [
            "example.com",
            "example.com:",
            "example.com:abc",
            "example.com:70000",
            "example.com:0",
            "2001:db8::1:443",
            ":443",
            "evil..com:443",
            "exa mple.com:443",
            "[::1]",
        ]
        with AllowlistProxy({"example.com"}) as proxy:
            before = proxy.blocked_count
            for authority in malformed:
                with self.subTest(authority=authority):
                    self._raw(proxy, ("CONNECT %s HTTP/1.1\r\nHost: %s\r\n\r\n" % (authority, authority)).encode("latin-1"), "HTTP/1.1 400")
            self.assertGreater(proxy.blocked_count, before)
            self.assertEqual(proxy.allowed_count, 0)
            self.assertIn("<malformed>", proxy.blocked_hosts)

    def test_connect_no_tunnel_on_ambiguous_authority(self):
        with AllowlistProxy({"2001:db8::1", "example.com"}) as proxy:
            self._raw(proxy, b"CONNECT 2001:db8::1:443 HTTP/1.1\r\nHost: 2001:db8::1\r\n\r\n", "HTTP/1.1 400")
            self.assertEqual(proxy.allowed_count, 0)
            self.assertGreaterEqual(proxy.blocked_count, 1)
            self.assertIn("<malformed>", proxy.blocked_hosts)

    def test_connect_trailing_dot_tunneled(self):
        with AllowlistProxy({"127.0.0.1"}) as proxy:
            host, port_text = proxy.address.split(":")
            client = socket.create_connection((host, int(port_text)), timeout=10)
            client.sendall(("CONNECT 127.0.0.1.:%d HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n\r\n" % (self.upstream.port, self.upstream.port)).encode("latin-1"))
            response = client.recv(4096).decode("latin-1")
            self.assertTrue(response.startswith("HTTP/1.1 200"), response)
            client.sendall(b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
            data = b""
            client.settimeout(10)
            try:
                while True:
                    chunk = client.recv(4096)
                    if not chunk:
                        break
                    data += chunk
            except socket.timeout:
                pass
            client.close()
            self.assertIn(b"upstream-ok", data)
            self.assertEqual(proxy.allowed_count, 1)

    def test_http_split_brain_host_rejected(self):
        with AllowlistProxy({"example.com"}) as proxy:
            self._raw(proxy, b"GET http://example.com/ok HTTP/1.1\r\nHost: evil.example.net\r\n\r\n", "HTTP/1.1 400")
            self.assertEqual(proxy.allowed_count, 0)
            self.assertGreaterEqual(proxy.blocked_count, 1)
            self.assertIn("example.com", proxy.blocked_hosts)

    def test_http_missing_host_header_rejected(self):
        with AllowlistProxy({"example.com"}) as proxy:
            self._raw(proxy, b"GET http://example.com/ok HTTP/1.1\r\n\r\n", "HTTP/1.1 400")
            self.assertEqual(proxy.allowed_count, 0)

    def test_http_duplicate_host_header_rejected(self):
        with AllowlistProxy({"example.com"}) as proxy:
            self._raw(proxy, b"GET http://example.com/ok HTTP/1.1\r\nHost: example.com\r\nHost: evil.example.net\r\n\r\n", "HTTP/1.1 400")
            self.assertEqual(proxy.allowed_count, 0)

    def test_first_line_length_cap_closed_431(self):
        with AllowlistProxy({"example.com"}) as proxy:
            self._raw(proxy, b"GET " + b"A" * 20000 + b" HTTP/1.1\r\n\r\n", "HTTP/1.1 431")
            self.assertIn("<malformed>", proxy.blocked_hosts)

    def test_total_header_cap_closed_431(self):
        with AllowlistProxy({"example.com"}) as proxy:
            payload = b"GET http://example.com/ok HTTP/1.1\r\nX-Big: " + b"B" * 70000 + b"\r\n"
            self._raw(proxy, payload, "HTTP/1.1 431")
            self.assertEqual(proxy.allowed_count, 0)


if __name__ == "__main__":
    unittest.main()
