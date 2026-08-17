"""noesis_harness/context_pack.py

Pack memory into a hard token budget (chars/4). L0 first, promote L1 only
if budget remains. OpenViking/Anthropic compaction without a server.
"""

from __future__ import annotations


def estimate_tokens(text):
    return max(1, (len(text or "") + 3) // 4)


class ContextPack:
    def __init__(self, memory, vfs=None, max_tokens=800):
        self.memory = memory
        self.vfs = vfs
        self.max_tokens = int(max_tokens)

    def pack(self, query, limit=12):
        hits = self.memory.recall(query, limit=limit)
        used = 0
        items = []
        for h in hits:
            mid = h.get("id", "")
            fact = h.get("fact") or ""
            text = fact
            level = "L2"
            if self.vfs and mid:
                l0 = self.vfs.resolve(mid, "L0")
                text = l0.get("text") or fact
                level = "L0"
            cost = estimate_tokens(text)
            if used + cost > self.max_tokens:
                continue
            used += cost
            rec = {"id": mid, "level": level, "text": text, "tokens": cost}
            items.append(rec)
        leftover = self.max_tokens - used
        if leftover > 40 and self.vfs:
            promoted = []
            for rec in items:
                if leftover <= 40:
                    break
                l1 = self.vfs.resolve(rec["id"], "L1")
                extra = estimate_tokens(l1.get("text") or "") - rec["tokens"]
                if extra <= leftover:
                    rec["text"] = l1.get("text") or rec["text"]
                    rec["level"] = "L1"
                    rec["tokens"] += max(0, extra)
                    leftover -= max(0, extra)
                promoted.append(rec)
            items = promoted or items
            used = self.max_tokens - leftover
        return {"items": items, "tokens": used, "budget": self.max_tokens,
                "ok": used <= self.max_tokens}
