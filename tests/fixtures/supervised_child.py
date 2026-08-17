"""Tiny stdlib child used only by supervisor lifecycle tests."""
import argparse
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"status": "ready", "contract_version": "1.0", "data": {"readiness": "ready"}}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--crash-after", type=float, default=0.0)
    args = parser.parse_args()
    host = os.environ["NOESIS_HOST"]
    port = int(os.environ["NOESIS_PORT"])
    server = ThreadingHTTPServer((host, port), Handler)
    if args.crash_after > 0:
        threading.Timer(args.crash_after, server.shutdown).start()
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
