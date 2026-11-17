"""addons/t_search_bridge.py

Optional, disabled-by-default bridge between NOESIS agent memory and the
external "t-search-harness" retriever (https://github.com/turbo-llm/t-search-harness,
Apache-2.0, T-Search model).

WHY THIS LIVES IN addons/ AND NOT IN noesis_harness/
---------------------------------------------------
AGENTS.md rule 1 (zero dependencies) forbids adding third-party packages to the
core. t-search-harness pulls in `openai`, `pydantic`, `pydantic-settings`,
`pyyaml`, so it must never be imported by noesis_harness/. This module is a
separate, optional adapter. It imports the heavy retriever_agent package
LAZILY (only inside `retrieve`) so importing this module never requires
t-search-harness to be installed.

INTEGRATION SHAPE (Track C: memory long-context)
------------------------------------------------
NOESIS stores memory as an append-only event log. t-search-harness is a
round-based retrieval/ranking lens that expects an operator-supplied search
backend. We satisfy that contract with `NoesisMemorySearchClient`, which serves
the NOESIS event log itself as the corpus. Concretely: an agent asks
`retrieve(query)` and t-search ranks the most relevant events from NOESIS memory,
returning a focused context instead of the whole projection. This is a
PLUGGABLE retrieval callback (AGENTS.md rule 2): core recall stays
deterministic and LLM-free; this lens is used only when an operator explicitly
enables it and supplies an OpenAI-compatible LLM endpoint.

HONESTY BOUNDARY
----------------
- Disabled by default. `retrieve` returns status `not_run` when not enabled.
- If t-search-harness is not installed, or no LLM endpoint is configured, the
  bridge fails closed with status `blocked` and a reason. It never claims the
  memory was "improved" or that a run succeeded when it did not.
- t-search-harness is tuned for the T-Search model; behavior on other models is
  best-effort and must not be advertised as a parity or superiority claim.

Zero hard dependency on retriever_agent at import time.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from noesis_harness.event_store import EventStore


@dataclass
class TSearchBridgeConfig:
    """Operator-controlled configuration for the optional t-search lens.

    Keep this stdlib-only (no pydantic) so the bridge can be constructed and
    inspected without t-search-harness installed.
    """

    enabled: bool = False
    llm_endpoints: List[str] = field(default_factory=list)
    model: Optional[str] = None
    max_rounds: int = 5
    max_results: int = 10
    budget_tokens: int = 32768
    temperature: float = 0.7
    top_p: float = 1.0
    extra: Dict[str, Any] = field(default_factory=dict)


class NoesisMemorySearchClient:
    """SearchClient Protocol adapter over a NOESIS EventStore JSONL log.

    This is the "bring your own retriever" backend for t-search-harness. It
    treats the NOESIS event log as the corpus so the lens can rank the agent's
    own memory without an external vector DB. A trivial keyword scorer is used;
    swap this class for a real retriever (BM25, embeddings) if desired.

    Contract (matches t-search-harness SearchClient):
        search(query: str, top_k: int) -> str  # JSON list of
        {"docid": str, "snippet": str, "score": float}
    """

    def __init__(self, events_path: str, max_snippet_chars: int = 400):
        self.events_path = events_path
        self.max_snippet_chars = max_snippet_chars

    def _score(self, query: str, text: str) -> float:
        q = query.lower()
        t = text.lower()
        if not q:
            return 0.0
        terms = [p for p in q.split() if p]
        if not terms:
            return 1.0 if q in t else 0.0
        return float(sum(1 for term in terms if term in t)) / float(len(terms))

    def search(self, query: str, top_k: int) -> str:
        if not os.path.exists(self.events_path):
            return "[]"
        store = EventStore(self.events_path)
        scored = []  # type: List[Dict[str, Any]]
        for rec in store.iter_events():
            if not isinstance(rec, dict):
                continue
            event_id = str(rec.get("event_id", ""))
            payload = rec.get("payload", rec)
            try:
                text = json.dumps(payload, ensure_ascii=False, default=str)
            except (TypeError, ValueError):
                text = str(payload)
            score = self._score(query, text)
            if score <= 0.0:
                continue
            snippet = text[: self.max_snippet_chars]
            scored.append(
                {
                    "docid": event_id,
                    "snippet": snippet,
                    "score": round(score, 4),
                }
            )
        scored.sort(key=lambda d: d["score"], reverse=True)
        return json.dumps(scored[:top_k], ensure_ascii=False)


def _disabled_result(reason: str) -> Dict[str, Any]:
    return {
        "status": "not_run",
        "reason": reason,
        "documents": [],
        "telemetry": {},
    }


def _blocked_result(reason: str) -> Dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "documents": [],
        "telemetry": {},
    }


def retrieve(query: str, config: TSearchBridgeConfig, events_path: str) -> Dict[str, Any]:
    """Run the t-search retrieval lens over NOESIS memory.

    Fails closed (not_run / blocked) whenever the bridge is not enabled, the
    harness is not installed, or no LLM endpoint is supplied. Only performs
    external/LLM work when fully configured.
    """
    if not config.enabled:
        return _disabled_result("bridge disabled (TSearchBridgeConfig.enabled=False)")
    if not config.llm_endpoints:
        return _blocked_result("no LLM endpoint configured (needs OpenAI-compatible URL)")

    try:
        from retriever_agent import (  # type: ignore
            AgentConfig,
            OpenAILLMClient,
            RetrieverAgent,
        )
        from retriever_agent.clients.search import HttpSearchClient  # noqa: F401
    except Exception as exc:  # ImportError or any harness load failure
        return _blocked_result("t-search-harness not installed: %s" % exc)

    if not os.path.exists(events_path):
        return _blocked_result("NOESIS event log not found at %s" % events_path)

    kwargs = dict(
        model=config.model or "t-tech/T-Search",
        temperature=config.temperature,
        top_p=config.top_p,
        max_rounds=config.max_rounds,
        max_results=config.max_results,
        budget_tokens=config.budget_tokens,
    )
    kwargs.update(config.extra or {})
    agent_config = AgentConfig(**kwargs)
    llm = OpenAILLMClient(config.llm_endpoints, agent_config)
    search = NoesisMemorySearchClient(events_path)
    agent = RetrieverAgent(agent_config, llm, search)

    result = agent.retrieve(query)
    documents = [
        {
            "chunk_id": d.chunk_id,
            "text": d.text,
            "score": d.score,
            "rank": d.rank,
            "retrieval_query": d.retrieval_query,
        }
        for d in result.documents
    ]
    return {
        "status": "ok",
        "documents": documents,
        "telemetry": {
            "rounds_completed": getattr(result, "rounds_completed", None),
            "tool_call_counts": getattr(result, "tool_call_counts", None),
        },
    }
