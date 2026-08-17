"""noesis_harness/session.py

Rule extract: working observations -> 1 episodic summary + semantic bullets.
No LLM. Optional Memory.compressor still applies on save.
"""

from __future__ import annotations

import re


_WORD = re.compile(r"[A-Za-zА-Яа-я0-9]{4,}")


def extract_session(memory, session_id, limit=5):
    with memory._conn() as c:
        rows = c.execute(
            "SELECT kind, content FROM observations WHERE session_id=? "
            "ORDER BY created_at ASC", (session_id,)).fetchall()
    texts = [r["content"] for r in rows if r["content"]]
    if not texts:
        return {"summary_id": "", "fact_ids": [], "n_obs": 0}
    joined = " | ".join(texts)
    summary_id = memory.summarize(session_id, "session %s: %s" % (session_id, joined[:400]))
    freq = {}
    for t in texts:
        for w in _WORD.findall(t.lower()):
            freq[w] = freq.get(w, 0) + 1
    top = sorted(freq, key=lambda w: (-freq[w], w))[:limit]
    fact_ids = []
    if top:
        fact_ids.append(memory.save(
            "session %s keywords: %s" % (session_id, ", ".join(top)),
            kind="semantic", confidence=0.4))
    first = texts[0][:240]
    fact_ids.append(memory.save(
        "session %s first: %s" % (session_id, first),
        kind="semantic", confidence=0.5))
    return {"summary_id": summary_id, "fact_ids": fact_ids, "n_obs": len(texts)}
