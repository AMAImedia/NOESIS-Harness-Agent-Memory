"""addons/vec_adapter.py

Optional, disabled-by-default vector-store adapter that provides pluggable
embedding-based similarity search over text items.

BORROWED PATTERNS
-----------------
- agentmemory: the "memory is a replay projection, storage never calls an LLM"
  discipline. We extend it: vector search is an optional index bolted on top of
  the deterministic core, never required by it.
- LoopX: the "addon that degrades to a no-op when the optional backend is
  absent" pattern. LoopX ships heavy integrations as soft dependencies so the
  core never hard-requires them. We mirror that: this module lives in addons/
  (not noesis_harness/) and only touches an embedding library lazily, inside the
  functions that need it.

WHY LAZY + DISABLED-BY-DEFAULT
------------------------------
AGENTS.md rule 1 (zero dependencies) forbids third-party packages in the core.
A vector store needs an embedding backend (e.g. sentence-transformers, numpy),
which is heavy and optional. This module must therefore:
  * import cleanly even when NO embedding library is installed, and
  * never raise on missing dependencies -- instead return a clear "disabled"
    dict (status == "disabled", results == []) so callers can branch without
    try/except.

The embedding backend is pluggable: callers may inject an `embedder` callable
(embedding lib of their choice). If none is injected, the adapter attempts a
single lazy import of a configurable module name; on failure every operation
reports "disabled".

Every public method guards on import/compute failure and returns the disabled
shape. There is no global state that imports an embedding lib at module load.

HONESTY BOUNDARY
----------------
- If the backend is missing, `index_texts` and `search` report status
  "disabled" and do nothing. They never claim texts were indexed or a match
  was found.
- `search` always returns `results` as a list, even in disabled mode.

Zero hard dependency on any embedding library at import time.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


DEFAULT_EMBEDDER_MODULE = "sentence_transformers"


def _disabled_result(reason: str, results: Optional[List[Any]] = None) -> Dict[str, Any]:
    return {
        "status": "disabled",
        "reason": reason,
        "indexed": 0,
        "results": results if results is not None else [],
    }


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    norm_a = math.sqrt(sum(float(x) * float(x) for x in a))
    norm_b = math.sqrt(sum(float(x) * float(x) for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class VecStore:
    """Pluggable, optional vector store for text similarity search.

    Instances are not required to be thread-safe for the disabled path; the
    disabled path is side-effect free and safe to call from any thread.
    """

    def __init__(
        self,
        embedder: Optional[Callable[[List[str]], List[List[float]]]] = None,
        embedder_module: str = DEFAULT_EMBEDDER_MODULE,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self._embedder = embedder
        self._embedder_module = embedder_module
        self._model_name = model_name
        self._texts: List[str] = []
        self._vectors: List[List[float]] = []

    def _resolve_embedder(self) -> Optional[Callable[[List[str]], List[List[float]]]]:
        """Return a callable that embeds a list of texts, or None if unavailable.

        Never raises: import and construction failures degrade to None.
        """
        if self._embedder is not None:
            return self._embedder
        try:
            mod = __import__(self._embedder_module, fromlist=["SentenceTransformer"])
            model = getattr(mod, "SentenceTransformer")(self._model_name)
            def _embed(texts: List[str]) -> List[List[float]]:
                return [list(vec) for vec in model.encode(texts)]
            return _embed
        except Exception:
            return None

    def index_texts(self, items: Sequence[Any]) -> Dict[str, Any]:
        """Index a list of text items for later similarity search.

        Each item may be a plain string or a dict with at least a "text" key.
        Returns status "ok" with the count indexed, or status "disabled" when
        no embedding backend is available. Never raises on a missing backend.
        """
        embedder = self._resolve_embedder()
        if embedder is None:
            return _disabled_result(
                "embedding backend unavailable (%s not installed)" % self._embedder_module
            )

        texts: List[str] = []
        for item in items:
            if isinstance(item, dict):
                text = item.get("text")
            else:
                text = item
            if text is None:
                continue
            texts.append(str(text))

        if not texts:
            return {"status": "ok", "indexed": 0, "results": []}

        try:
            vectors = embedder(texts)
        except Exception as exc:
            return _disabled_result("embedding failed: %s" % exc)

        self._texts.extend(texts)
        self._vectors.extend(vectors)
        return {"status": "ok", "indexed": len(texts), "results": []}

    def search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Return the top_k most similar indexed texts to `query`.

        Returns status "disabled" with an empty results list when no embedding
        backend is available. Never raises on a missing backend. When the index
        is empty (but a backend exists) returns status "ok" with empty results.
        """
        embedder = self._resolve_embedder()
        if embedder is None:
            return _disabled_result(
                "embedding backend unavailable (%s not installed)" % self._embedder_module
            )

        if not self._texts:
            return {"status": "ok", "indexed": 0, "results": []}

        try:
            q_vec = embedder([str(query)])[0]
        except Exception as exc:
            return _disabled_result("embedding failed: %s" % exc)

        scored: List[Tuple[float, str]] = []
        for text, vec in zip(self._texts, self._vectors):
            scored.append((_cosine_similarity(q_vec, vec), text))

        scored.sort(key=lambda t: t[0], reverse=True)
        top_k = max(0, int(top_k))
        results = [{"text": text, "score": score} for score, text in scored[:top_k]]
        return {"status": "ok", "indexed": len(self._texts), "results": results}
