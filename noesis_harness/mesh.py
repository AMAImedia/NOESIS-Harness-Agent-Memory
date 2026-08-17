"""noesis_harness/mesh.py

Local P2P memory sync: shared-folder snapshots + optional stdlib HTTP peer.

Pattern adapted from agentmemory mesh.ts (LWW pull/push, no central broker).
No cloud vendor. Two laptops sync via a folder or http://host:port/snapshot.
"""

from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .snapshot import export_snapshot, import_snapshot


class Mesh:
    """Push local memory to a folder; pull every *.json peer snapshot (LWW)."""

    def __init__(self, memory, peer_dir, node_id="local"):
        self.memory = memory
        self.peer_dir = peer_dir
        self.node_id = node_id
        os.makedirs(peer_dir, exist_ok=True)

    def local_path(self):
        return os.path.join(self.peer_dir, "%s.json" % self.node_id)

    def push(self):
        return export_snapshot(self.memory, self.local_path())

    def pull(self):
        merged = 0
        if not os.path.isdir(self.peer_dir):
            return 0
        for name in os.listdir(self.peer_dir):
            if not name.endswith(".json"):
                continue
            if name == "%s.json" % self.node_id:
                continue
            path = os.path.join(self.peer_dir, name)
            try:
                merged += import_snapshot(self.memory, path)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
        return merged

    def sync(self):
        pulled = self.pull()
        pushed = self.push()
        return {"pulled": pulled, "pushed": pushed, "at": time.time()}


def serve_mesh(memory, host="127.0.0.1", port=8765):
    """HTTP peer: GET /snapshot, PUT /snapshot (JSON body). Returns server."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_GET(self):
            if self.path.rstrip("/") != "/snapshot":
                self.send_error(404)
                return
            tmp = os.path.join(os.path.dirname(memory.db_path) or ".", "_mesh_http.json")
            export_snapshot(memory, tmp)
            with open(tmp, "rb") as fh:
                body = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_PUT(self):
            if self.path.rstrip("/") != "/snapshot":
                self.send_error(404)
                return
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n)
            tmp = os.path.join(os.path.dirname(memory.db_path) or ".", "_mesh_in.json")
            with open(tmp, "wb") as fh:
                fh.write(raw)
            merged = import_snapshot(memory, tmp)
            body = json.dumps({"ok": True, "merged": merged}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    httpd = ThreadingHTTPServer((host, port), Handler)
    return httpd
