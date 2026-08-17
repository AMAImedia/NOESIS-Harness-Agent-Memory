"""noesis_harness/mcp_stdio.py

Minimal MCP stdio server (JSON-RPC 2.0 subset). Stdlib only.

Tools: memory_save, memory_recall, queue_enqueue, trace_record, hitl_draft.
Not a full MCP SDK — enough for Claude/Codex to attach locally.
"""

from __future__ import annotations

import json
import sys


TOOLS = [
    {"name": "memory_save", "description": "Save a semantic fact",
     "inputSchema": {"type": "object", "properties": {"fact": {"type": "string"}},
                     "required": ["fact"]}},
    {"name": "memory_recall", "description": "Recall facts",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}},
                     "required": ["query"]}},
    {"name": "queue_enqueue", "description": "Enqueue a JSON payload",
     "inputSchema": {"type": "object", "properties": {"payload": {"type": "object"}},
                     "required": ["payload"]}},
    {"name": "trace_record", "description": "Append an agent trace step",
     "inputSchema": {"type": "object",
                     "properties": {"kind": {"type": "string"}, "payload": {"type": "object"}},
                     "required": ["kind"]}},
    {"name": "hitl_draft", "description": "Create a HITL draft (never sent)",
     "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}},
                     "required": ["text"]}},
]


class McpServer:
    def __init__(self, memory=None, queue=None, trace=None, hitl=None):
        self.memory = memory
        self.queue = queue
        self.trace = trace
        self.hitl = hitl

    def handle(self, msg):
        method = msg.get("method")
        mid = msg.get("id")
        params = msg.get("params") or {}
        if method == "initialize":
            return self._ok(mid, {"protocolVersion": "2024-11-05",
                                  "capabilities": {"tools": {}},
                                  "serverInfo": {"name": "noesis-harness", "version": "0.5.0"}})
        if method == "tools/list":
            return self._ok(mid, {"tools": TOOLS})
        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            try:
                text = self._call(name, args)
                return self._ok(mid, {"content": [{"type": "text", "text": text}]})
            except Exception as exc:
                return {"jsonrpc": "2.0", "id": mid,
                        "error": {"code": -32000, "message": str(exc)}}
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": "unknown method"}}

    def _call(self, name, args):
        if name == "memory_save":
            if not self.memory:
                raise RuntimeError("memory not wired")
            return self.memory.save(args["fact"])
        if name == "memory_recall":
            if not self.memory:
                raise RuntimeError("memory not wired")
            hits = self.memory.recall(args["query"], limit=5)
            return json.dumps([h.get("fact") for h in hits], ensure_ascii=False)
        if name == "queue_enqueue":
            if not self.queue:
                raise RuntimeError("queue not wired")
            return self.queue.enqueue(args.get("payload") or {})
        if name == "trace_record":
            if not self.trace:
                raise RuntimeError("trace not wired")
            return self.trace.record(args.get("kind", "step"), args.get("payload") or {})
        if name == "hitl_draft":
            if not self.hitl:
                raise RuntimeError("hitl not wired")
            return self.hitl.draft(args["text"])
        raise RuntimeError("unknown tool")

    @staticmethod
    def _ok(mid, result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def serve(self, stdin=None, stdout=None):
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            out = self.handle(msg)
            stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            stdout.flush()
