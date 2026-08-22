import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from noesis_harness.coding_backend import (
    BoundedCodingBackend,
    CodingBackendError,
    LocalHTTPCodingBackend,
)


class _Handler(BaseHTTPRequestHandler):
    response = {"response": "generated patch"}
    response_bytes = None

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        self.server.last_body = self.rfile.read(length)
        raw = self.response_bytes
        if raw is None:
            raw = json.dumps(self.response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_args):
        return


class CodingBackendTests(unittest.TestCase):
    def test_requires_explicit_argv_and_existing_worktree(self):
        with TemporaryDirectory() as root:
            with self.assertRaisesRegex(CodingBackendError, "explicit_argv_required"):
                BoundedCodingBackend([], Path(root))
            with self.assertRaisesRegex(CodingBackendError, "worktree_missing"):
                BoundedCodingBackend([sys.executable, "-c", "pass"], Path(root) / "missing")

    def test_success_and_output_bound(self):
        with TemporaryDirectory() as root:
            result = BoundedCodingBackend([sys.executable, "-c", "print('x' * 100)"], Path(root), output_limit=16).run()
            self.assertEqual(result.status, "passed")
            self.assertEqual(result.returncode, 0)
            self.assertLessEqual(len(result.stdout), 16)
            self.assertEqual(result.reason, "process_completed")

    def test_timeout_is_fail_closed(self):
        with TemporaryDirectory() as root:
            result = BoundedCodingBackend([sys.executable, "-c", "import time; time.sleep(30)"], Path(root), timeout_seconds=0.05).run()
            self.assertEqual(result.status, "timeout")
            self.assertIsNone(result.returncode)
            self.assertEqual(result.reason, "process_timeout")

    def _serve(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def cleanup():
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()
        self.addCleanup(cleanup)
        return server

    def test_local_http_success_uses_explicit_code_contract(self):
        server = self._serve()
        backend = LocalHTTPCodingBackend(
            f"http://127.0.0.1:{server.server_port}/api/chat",
            "repair the failing test",
            timeout_seconds=2,
        )
        result = backend.run()
        self.assertEqual(result.status, "passed")
        self.assertEqual(result.reason, "http_completed")
        self.assertEqual(result.stdout, "generated patch")
        body = json.loads(server.last_body.decode("utf-8"))
        self.assertEqual(body["preset"], "code")
        self.assertEqual(body["message"], "repair the failing test")

    def test_local_http_rejects_malformed_response(self):
        _Handler.response = {"unexpected": 1}
        self.addCleanup(setattr, _Handler, "response", {"response": "generated patch"})
        server = self._serve()
        result = LocalHTTPCodingBackend(f"http://127.0.0.1:{server.server_port}/api/chat", "prompt", timeout_seconds=2).run()
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "response_text_missing")

    def test_local_http_rejects_oversized_response(self):
        _Handler.response_bytes = b'"' + (b"x" * 32) + b'"'
        self.addCleanup(setattr, _Handler, "response_bytes", None)
        server = self._serve()
        result = LocalHTTPCodingBackend(f"http://127.0.0.1:{server.server_port}/api/chat", "prompt", output_limit=8, timeout_seconds=2).run()
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "response_output_limit_exceeded")


if __name__ == "__main__":
    unittest.main()
