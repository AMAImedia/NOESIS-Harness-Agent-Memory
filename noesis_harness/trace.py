"""noesis_harness/trace.py

AgentTrace + hybrid judge (rules first, optional LLM callback).

Pattern adapted from evalscope llm_recall / hybrid judge: deterministic
gates never need a model; a judge_fn is only for graded quality.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid


class AgentTrace:
    """Append-only JSONL of agent steps (input/output/tool/error)."""

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def record(self, kind, payload, step_id=None):
        rec = {
            "id": step_id or uuid.uuid4().hex,
            "kind": kind,
            "payload": payload,
            "ts": time.time(),
        }
        line = json.dumps(rec, ensure_ascii=False, default=str) + "\n"
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line)
        return rec["id"]

    def load(self, limit=200):
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
        return out[-limit:]


class HybridJudge:
    """Fail-closed rule judge + optional graded callback.

    Rules (always on):
      - empty output
      - exact loop (same output twice in a row)
      - overlong output
    Optional judge_fn(trace_rows) -> {score, reason}.
    """

    def __init__(self, max_chars=4000, judge_fn=None):
        self.max_chars = max_chars
        self.judge_fn = judge_fn

    def judge(self, outputs, traces=None):
        texts = [str(x or "") for x in (outputs or [])]
        reasons = []
        score = 1.0
        if not texts or not any(t.strip() for t in texts):
            return {"pass": False, "score": 0.0, "reasons": ["empty_output"]}
        if any(len(t) > self.max_chars for t in texts):
            reasons.append("overlong")
            score -= 0.3
        if len(texts) >= 2 and texts[-1] == texts[-2]:
            reasons.append("exact_loop")
            score -= 0.5
        graded = None
        if self.judge_fn is not None:
            try:
                graded = self.judge_fn(traces if traces is not None else texts)
                if isinstance(graded, dict) and "score" in graded:
                    score = min(score, float(graded["score"]))
                    if graded.get("reason"):
                        reasons.append(str(graded["reason"]))
            except Exception as exc:
                reasons.append("judge_fn_error:%s" % exc)
        score = max(0.0, min(1.0, score))
        hard = {"empty_output", "exact_loop"}
        return {"pass": score >= 0.5 and not (hard & set(reasons)),
                "score": score, "reasons": reasons, "graded": graded}
