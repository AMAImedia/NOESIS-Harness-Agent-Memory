"""noesis_harness/vfs.py

OpenViking-style progressive load without a server.

URI: noesis://{tier}/{id}
  L0 abstract  (~1 sentence)
  L1 overview  (first ~400 chars + meta)
  L2 details   (full offload file or fact)
"""

from __future__ import annotations

import os
import re


def uri(tier, item_id):
    return "noesis://%s/%s" % (tier, item_id)


def parse_uri(value):
    m = re.match(r"^noesis://(L0|L1|L2|working|episodic|semantic|procedural)/(.+)$", value or "")
    if not m:
        return None
    return {"tier": m.group(1), "id": m.group(2)}


def _clip(text, n):
    text = (text or "").strip()
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0] + "..."


class ContextVfs:
    def __init__(self, memory, ref_dir=""):
        self.memory = memory
        self.ref_dir = ref_dir

    def put_offload(self, session_id, text):
        if not self.ref_dir:
            raise ValueError("ref_dir required")
        return self.memory.offload(session_id, text, self.ref_dir)

    def resolve(self, item_id, level="L1"):
        fact = self._fact(item_id)
        body = fact or self._file(item_id) or ""
        if level == "L0":
            return {"uri": uri("L0", item_id), "text": _clip(body, 120), "level": "L0"}
        if level == "L1":
            return {"uri": uri("L1", item_id), "text": _clip(body, 400), "level": "L1"}
        return {"uri": uri("L2", item_id), "text": body, "level": "L2"}

    def ls(self, kind="semantic", limit=20):
        rows = self.memory.profile(kind=kind, limit=limit)
        return [uri("semantic", r["id"]) for r in rows]

    def _fact(self, item_id):
        with self.memory._conn() as c:
            row = c.execute("SELECT fact FROM memories WHERE id=?", (item_id,)).fetchone()
            if row:
                return row["fact"]
            row = c.execute("SELECT text FROM summaries WHERE id=? OR session_id=?",
                            (item_id, item_id)).fetchone()
            if row:
                return row["text"]
        return ""

    def _file(self, item_id):
        if not self.ref_dir:
            return ""
        path = os.path.join(self.ref_dir, "%s.md" % item_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
        return ""
