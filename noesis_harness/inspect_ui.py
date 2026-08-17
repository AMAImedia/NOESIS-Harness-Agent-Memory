"""noesis_harness/inspect_ui.py

Stdlib HTTP inspector for memory + event log. No JS framework, no deps.

Not a product UI — a local debug surface so you can see state without sqlite3 CLI.
"""

from __future__ import annotations

import html
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _page(title, body):
    return (
        "<!doctype html><meta charset=utf-8><title>%s</title>"
        "<style>body{font:14px/1.4 sans-serif;max-width:960px;margin:24px auto;"
        "padding:0 16px}table{border-collapse:collapse;width:100%%}"
        "td,th{border:1px solid #ccc;padding:4px 8px;text-align:left}"
        "a{color:#06c}</style><h1>%s</h1>%s"
    ) % (html.escape(title), html.escape(title), body)


class InspectUI:
    def __init__(self, memory=None, event_store=None):
        self.memory = memory
        self.event_store = event_store

    def render_index(self):
        stats = self.memory.stats() if self.memory else {}
        rows = "".join("<tr><th>%s</th><td>%s</td></tr>" % (html.escape(str(k)), html.escape(str(v)))
                       for k, v in stats.items())
        body = "<p><a href='/memories'>memories</a> · <a href='/events'>events</a></p>"
        body += "<table>%s</table>" % rows
        return _page("NOESIS inspect", body)

    def render_memories(self):
        if not self.memory:
            return _page("memories", "<p>no memory</p>")
        items = self.memory.profile(limit=50)
        rows = ["<tr><th>kind</th><th>str</th><th>fact</th></tr>"]
        for r in items:
            rows.append("<tr><td>%s</td><td>%.2f</td><td>%s</td></tr>" % (
                html.escape(str(r.get("kind", ""))),
                float(r.get("strength") or 0),
                html.escape(str(r.get("fact", ""))[:240]),
            ))
        return _page("memories", "<p><a href='/'>back</a></p><table>%s</table>" % "".join(rows))

    def render_events(self):
        if not self.event_store or not os.path.exists(self.event_store.path):
            return _page("events", "<p><a href='/'>back</a></p><p>no events</p>")
        lines = []
        with open(self.event_store.path, "r", encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if i >= 80:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    lines.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                        html.escape(str(rec.get("seq", ""))),
                        html.escape(str(rec.get("type", ""))),
                        html.escape(json.dumps(rec.get("payload"), ensure_ascii=False)[:200]),
                    ))
                except ValueError:
                    continue
        table = "<tr><th>seq</th><th>type</th><th>payload</th></tr>" + "".join(lines)
        return _page("events", "<p><a href='/'>back</a></p><table>%s</table>" % table)

    def serve(self, host="127.0.0.1", port=8787):
        ui = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                return

            def do_GET(self):
                path = self.path.split("?", 1)[0].rstrip("/") or "/"
                if path == "/":
                    body = ui.render_index()
                elif path == "/memories":
                    body = ui.render_memories()
                elif path == "/events":
                    body = ui.render_events()
                else:
                    self.send_error(404)
                    return
                data = body.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        return ThreadingHTTPServer((host, port), Handler)


def main(argv=None):
    import argparse
    from .memory import Memory
    from .event_store import EventStore

    p = argparse.ArgumentParser(description="NOESIS local inspector")
    p.add_argument("--mem", default="state/mem.db")
    p.add_argument("--events", default="state/events.jsonl")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8787)
    args = p.parse_args(argv)
    mem = Memory(args.mem) if os.path.exists(args.mem) else None
    es = EventStore(args.events) if os.path.exists(args.events) else None
    httpd = InspectUI(mem, es).serve(args.host, args.port)
    print("inspect http://%s:%s" % (args.host, args.port))
    httpd.serve_forever()


if __name__ == "__main__":
    main()
