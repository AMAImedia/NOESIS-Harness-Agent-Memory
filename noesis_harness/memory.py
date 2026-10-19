"""noesis_harness/memory.py

Four-tier agent memory + hybrid keyword/FTS/vector search with RRF fusion.

Patterns adapted from:
  - agentmemory (4 tiers: working/episodic/semantic/procedural; BM25+vector+graph)
  - TencentDB-Agent-Memory (L0-L3 pyramid; symbolic offload of long logs)
  - Hermes Agent (SQLite + FTS5 for cross-session search)

Design:
  - Working  -> raw observations (bounded, per session)
  - Episodic -> session summaries ("what happened")
  - Semantic -> durable facts ("what I know") with confidence + decay
  - Procedural -> workflows ("how to do it") with trigger conditions
  - Vector   -> optional embeddings for semantic similarity (RRF fusion with BM25)

Zero dependencies (stdlib + sqlite3 FTS5). Vector tier is optional:
sentence-transformers + faiss/hnswlib degrade gracefully to pure Python cosine.
No LLM required for storage/recall (LLM only for compression, optional).
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import struct
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from .nextgen import _ManagedConnection
    from .resource_lineage import SENSITIVITIES
except ImportError:
    from nextgen import _ManagedConnection
    from resource_lineage import SENSITIVITIES

log = __import__("logging").getLogger(__name__)

#: What recall and profile return by default.
#:
#: Deny-by-default, matching ``experience_reuse.ExperienceReuseSelector``: a
#: record marked ``sensitive`` or ``restricted`` is stored and stays reachable
#: by id, but is never served into another context unless a caller asks for it
#: by name. That is the practical privacy control for an agent memory -- the
#: password is remembered, but it cannot be dragged back into the prompt.
DEFAULT_SENSITIVITIES: Tuple[str, ...] = ("public", "internal")


def check_sensitivity(value: str) -> str:
    """Validate a sensitivity label. Anything unknown is refused, not downgraded."""
    label = str(value or "").strip().lower()
    if label not in SENSITIVITIES:
        raise ValueError(
            "unknown_sensitivity: %r; expected one of %s"
            % (value, ", ".join(sorted(SENSITIVITIES)))
        )
    return label


def allowed_rows(
    rows: List[Dict[str, Any]], allowed: Sequence[str]
) -> List[Dict[str, Any]]:
    """Drop rows whose sensitivity is outside the allowed set.

    An empty allowed set returns nothing. That is the correct direction for a
    deny-by-default gate: an explicit "allow nothing" must not be read as
    "allow everything", because the caller who writes ``()`` is asking for the
    strictest answer and getting the loosest one would be the worst failure
    this function could have.

    Applied before ``_strengthen`` so that a suppressed row does not get its
    access count bumped. The counter is readable by anyone with the file, so
    bumping it would tell a watcher that a sensitive fact was matched even
    though it was never returned.
    """
    if not allowed:
        return []
    permitted = set(allowed)
    return [
        row
        for row in rows
        if str(row.get("sensitivity") or "internal").lower() in permitted
    ]


class Memory:
    """Four-tier persistent memory with hybrid FTS5+vector search, decay, and offload.

    Tiers:
      1. Working  -> raw observations (bounded, per session)
      2. Episodic -> session summaries ("what happened")
      3. Semantic -> durable facts ("what I know") with confidence + Ebbinghaus decay
      4. Proedural -> workflows ("how to do it") with trigger conditions
      5. Vector   -> optional embeddings for semantic similarity (RRF with BM25)

    Hybrid search: FTS5 (BM25) + vector (cosine) -> RRF fusion (w_BM25=0.4, w_vec=0.6).
    Decay: Ebbinghaus `strength *= 0.9^periods` (floor 0.1).
    Symbolic offload: long logs -> `refs/<session_id>.md` on disk.
    """

    DECAY_FLOOR = 0.1
    DECAY_RATE = 0.9        # strength *= rate^periods (Ebbinghaus)
    RRF_K = 60             # Reciprocal Rank Fusion constant
    RRF_W_BM25 = 0.4       # weight for BM25 rank
    RRF_W_VEC = 0.6        # weight for vector rank
    VEC_DUP_THRESHOLD = 0.95  # near-duplicate vector threshold
    VEC_MIN_SIM = 0.3      # minimum similarity for vector recall

    def __init__(self, db_path, compressor=None, rrf_w_bm25=None, rrf_w_vec=None, privacy=None):
        self.db_path = db_path
        self.compressor = compressor
        self.privacy = privacy
        self.rrf_w_bm25 = float(self.RRF_W_BM25 if rrf_w_bm25 is None else rrf_w_bm25)
        self.rrf_w_vec = float(self.RRF_W_VEC if rrf_w_vec is None else rrf_w_vec)
        self._lock = threading.Lock()
        self._vector_backend = None
        self._embed_model = None
        self._embed_dim = 0
        self._init()

    def _conn(self):
        c = sqlite3.connect(self.db_path, timeout=10, factory=_ManagedConnection)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def _init(self):
        with self._conn() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS observations (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
                    kind TEXT NOT NULL, content TEXT NOT NULL,
                    sensitivity TEXT NOT NULL DEFAULT 'internal',
                    created_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                    fact TEXT NOT NULL, confidence REAL NOT NULL DEFAULT 0.5,
                    strength REAL NOT NULL DEFAULT 1.0,
                    access_count INTEGER NOT NULL DEFAULT 0,
                    last_accessed_at REAL NOT NULL DEFAULT 0,
                    sensitivity TEXT NOT NULL DEFAULT 'internal',
                    created_at REAL NOT NULL,
                    embedding BLOB);
                CREATE TABLE IF NOT EXISTS summaries (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    sensitivity TEXT NOT NULL DEFAULT 'internal',
                    created_at REAL NOT NULL);
                CREATE VIRTUAL TABLE IF NOT EXISTS mem_fts USING fts5(
                    kind, fact, content='memories', content_rowid='rowid');
                CREATE INDEX IF NOT EXISTS idx_obs_session ON observations(session_id);
                CREATE INDEX IF NOT EXISTS idx_mem_kind ON memories(kind);
            """)
            c.executescript("""
                CREATE TRIGGER IF NOT EXISTS mem_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO mem_fts(rowid, kind, fact) VALUES (new.rowid, new.kind, new.fact);
                END;
                CREATE TRIGGER IF NOT EXISTS mem_ad AFTER DELETE ON memories BEGIN
                    INSERT INTO mem_fts(mem_fts, rowid, kind, fact)
                    VALUES ('delete', old.rowid, old.kind, old.fact);
                END;
            """)
            cols = {r[1] for r in c.execute("PRAGMA table_info(memories)").fetchall()}
            if "embedding" not in cols:
                c.execute("ALTER TABLE memories ADD COLUMN embedding BLOB")
            # Sensitivity arrives as a migration, not a schema rewrite: an
            # existing database keeps every row and every old row becomes
            # 'internal', which is still recalled. Deny-by-default applies to
            # what is written from here on, never silently to what was already
            # stored -- that would erase the memory's usefulness without
            # anyone being told.
            for table in ("memories", "observations", "summaries"):
                table_cols = {
                    r[1] for r in c.execute("PRAGMA table_info(%s)" % table).fetchall()
                }
                if "sensitivity" not in table_cols:
                    c.execute(
                        "ALTER TABLE %s ADD COLUMN sensitivity "
                        "TEXT NOT NULL DEFAULT 'internal'" % table
                    )

    # ==================================================================
    # Vector Tier (optional: sentence-transformers + faiss/hnswlib/numpy)
    # ==================================================================

    def _detect_vector_backend(self) -> str:
        """Detect the best available vector search backend."""
        if self._vector_backend is not None:
            return self._vector_backend
        env_override = os.environ.get("NOESIS_VECTOR_BACKEND")
        if env_override:
            self._vector_backend = env_override
            return env_override
        for name, mod in [("faiss", "faiss"), ("hnswlib", "hnswlib"), ("numpy", "numpy")]:
            try:
                __import__(mod)
                self._vector_backend = name
                return name
            except ImportError:
                continue
        self._vector_backend = "none"
        return "none"

    def _load_embed_model(self):
        """Lazy-load sentence-transformers model."""
        if self._embed_model is not None:
            return self._embed_model
        try:
            from sentence_transformers import SentenceTransformer
            self._embed_model = SentenceTransformer("all-MiniLM-L6-v2")
            self._embed_dim = 384
        except Exception:
            self._embed_model = None
        return self._embed_model

    def _embed(self, text: str) -> Optional[bytes]:
        """Generate a normalized embedding and serialize to bytes."""
        model = self._load_embed_model()
        if model is None:
            return None
        try:
            vec = model.encode(text, normalize_embeddings=True)
            arr = vec.tolist() if hasattr(vec, "tolist") else list(vec)
            return struct.pack(f"{len(arr)}f", *arr)
        except Exception:
            return None

    @staticmethod
    def _embed_to_list(blob: bytes) -> List[float]:
        n = len(blob) // 4
        return list(struct.unpack(f"{n}f", blob))

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na > 0 and nb > 0 else 0.0

    def save_vector(self, content: str, confidence: float = 0.5) -> str:
        """Save a fact + its vector embedding. Falls back to plain save."""
        if self._detect_vector_backend() == "none":
            return self.save(content, kind="semantic", confidence=confidence)
        emb = self._embed(content)
        if emb is None:
            return self.save(content, kind="semantic", confidence=confidence)
        mid = uuid.uuid4().hex
        with self._lock, self._conn() as c:
            # Near-duplicate check
            for row in c.execute(
                "SELECT id, embedding FROM memories WHERE embedding IS NOT NULL"
            ).fetchall():
                if row["embedding"]:
                    sim = self._cosine(self._embed_to_list(emb),
                                       self._embed_to_list(row["embedding"]))
                    if sim > self.VEC_DUP_THRESHOLD:
                        c.execute(
                            "UPDATE memories SET strength=MIN(2.0,strength+0.2),"
                            " access_count=access_count+1 WHERE id=?",
                            (row["id"],))
                        return row["id"]
            c.execute(
                "INSERT INTO memories (id, kind, fact, confidence, strength,"
                " created_at, embedding) VALUES (?,?,?,?,?,?,?)",
                (mid, "semantic", content, confidence, 1.0, time.time(), emb))
        return mid

    def _vector_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Vector similarity search. Returns ranked list."""
        if self._detect_vector_backend() == "none":
            return []
        q_emb = self._embed(query)
        if q_emb is None:
            return []
        q_list = self._embed_to_list(q_emb)
        scored: List[Tuple[float, Dict]] = []
        with self._conn() as c:
            for row in c.execute(
                "SELECT id, kind, fact, confidence, strength, embedding "
                "FROM memories WHERE embedding IS NOT NULL"
            ).fetchall():
                if row["embedding"]:
                    sim = self._cosine(q_list, self._embed_to_list(row["embedding"]))
                    if sim >= self.VEC_MIN_SIM:
                        d = dict(row)
                        d["_vec_score"] = sim
                        scored.append((sim, d))
        scored.sort(key=lambda x: -x[0])
        return [r for _, r in scored[:limit]]

    def _rrf_fuse(self, bm25_results: List[Dict], vec_results: List[Dict],
                  limit: int) -> List[Dict[str, Any]]:
        """Reciprocal Rank Fusion (BM25 w=0.4 + Vector w=0.6)."""
        k = self.RRF_K
        rrf: Dict[str, float] = {}
        merged: Dict[str, Dict] = {}
        for rank, r in enumerate(bm25_results):
            key = r.get("id", str(rank))
            rrf[key] = rrf.get(key, 0) + self.rrf_w_bm25 / (k + rank + 1)
            merged[key] = r
        for rank, r in enumerate(vec_results):
            key = r.get("id", str(rank))
            rrf[key] = rrf.get(key, 0) + self.rrf_w_vec / (k + rank + 1)
            merged[key] = r
        for key in merged:
            merged[key]["_rrf"] = rrf.get(key, 0)
        result = sorted(merged.values(), key=lambda x: -x.get("_rrf", 0))
        for r in result:
            r.pop("_rrf", None)
        return result[:limit]

    # ==================================================================
    # Working / Episodic
    # ==================================================================

    def observe(self, session_id, kind, content, sensitivity="internal"):
        if self.privacy is not None:
            content = self.privacy.scrub(content)
            if not content:
                return ""
        sensitivity = check_sensitivity(sensitivity)
        oid = uuid.uuid4().hex
        with self._lock, self._conn() as c:
            c.execute("INSERT INTO observations (id, session_id, kind, content, sensitivity, created_at)"
                      " VALUES (?,?,?,?,?,?)", (oid, session_id, kind, content, sensitivity, time.time()))
        return oid

    def summarize(self, session_id: str, text: str, sensitivity: str = "internal") -> str:
        sensitivity = check_sensitivity(sensitivity)
        sid = uuid.uuid4().hex
        with self._lock, self._conn() as c:
            c.execute("INSERT INTO summaries (id, session_id, text, sensitivity, created_at)"
                      " VALUES (?,?,?,?,?)", (sid, session_id, text, sensitivity, time.time()))
        return sid

    # ==================================================================
    # Semantic / Procedural
    # ==================================================================

    def save(self, fact, kind="semantic", confidence=0.5, sensitivity="internal"):
        """Save a durable fact/procedure. Supersedes an identical fact.

        ``sensitivity`` is validated and stored. It does not change what is
        written -- it changes what :meth:`recall` will hand back to anyone who
        did not name this fact directly.
        """
        if self.privacy is not None:
            fact = self.privacy.scrub(fact)
            if not fact:
                return ""
        if self.compressor is not None:
            try:
                fact = self.compressor(fact) or fact
            except Exception:
                pass
        sensitivity = check_sensitivity(sensitivity)
        mid = uuid.uuid4().hex
        with self._lock, self._conn() as c:
            row = c.execute("SELECT id FROM memories WHERE fact=?", (fact,)).fetchone()
            if row:
                c.execute("UPDATE memories SET strength=MIN(2.0, strength+0.2),"
                          " access_count=access_count+1 WHERE id=?", (row["id"],))
                return row["id"]
            c.execute("INSERT INTO memories (id, kind, fact, confidence, strength, "
                      "sensitivity, created_at)"
                      " VALUES (?,?,?,?,?,?,?)",
                      (mid, kind, fact, confidence, 1.0, sensitivity, time.time()))
        return mid

    def recall(self, query: str, limit: int = 10, kind: str = "",
               allowed_sensitivities: Sequence[str] = DEFAULT_SENSITIVITIES
               ) -> List[Dict[str, Any]]:
        """Hybrid recall: FTS5 + optional vector RRF fusion, then substring fallback.

        If vector backend is available and kind is not restricted, uses RRF fusion
        of BM25 (weight 0.4) and vector cosine (weight 0.6).
        Touches strength (access strengthens), applies decay lazily on read.

        ``allowed_sensitivities`` is the deny-by-default gate: records marked
        ``sensitive`` or ``restricted`` are stored and indexed, but are not
        returned unless the caller opts into them. The default returns only
        ``public`` and ``internal``; pass ``SENSITIVITIES`` to see everything;
        pass ``()`` for the strictest answer, which returns nothing at all.

        The filter runs *before* ``_strengthen`` on purpose. Suppressed rows
        must not accumulate access counts, because that counter lives in the
        same file and a watcher could read it back as evidence that a sensitive
        fact matched.
        """
        self.decay()

        if self._detect_vector_backend() != "none" and not kind:
            out = self._rrf_fuse(
                self._bm25_search(query, limit * 2),
                self._vector_search(query, limit * 2),
                limit)
        else:
            out = self._bm25_search(query, limit, kind)
        if len(out) < limit:
            extra = self._substring_search(query, limit - len(out), kind)
            seen = {r["id"] for r in out}
            for r in extra:
                if r["id"] not in seen:
                    out.append(r)

        out = allowed_rows(out, tuple(allowed_sensitivities or ()))
        self._strengthen(out)
        return out[:limit]

    def _bm25_search(self, query: str, limit: int,
                     kind: str = "") -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        try:
            with self._conn() as c:
                sql = ("SELECT m.*, bm25(mem_fts) AS score FROM mem_fts "
                       "JOIN memories m ON m.rowid = mem_fts.rowid "
                       "WHERE mem_fts MATCH ?")
                params: list = [query]
                if kind:
                    sql += " AND m.kind=?"
                    params.append(kind)
                sql += " ORDER BY score LIMIT ?"
                params.append(limit)
                rows = c.execute(sql, params).fetchall()
                out = [dict(r) for r in rows]
        except Exception:
            pass
        return out

    def _substring_search(self, query, limit, kind=""):
        out = []
        tokens = [t for t in (query or "").replace("-", " ").split() if len(t) >= 3]
        needles = [query] + tokens
        seen = set()
        try:
            with self._conn() as c:
                for needle in needles:
                    if not needle or len(out) >= limit:
                        break
                    sql = "SELECT * FROM memories WHERE fact LIKE ?"
                    params = ["%" + needle + "%"]
                    if kind:
                        sql += " AND kind=?"
                        params.append(kind)
                    sql += " ORDER BY strength DESC LIMIT ?"
                    params.append(limit)
                    for r in c.execute(sql, params).fetchall():
                        d = dict(r)
                        if d["id"] in seen:
                            continue
                        seen.add(d["id"])
                        out.append(d)
                        if len(out) >= limit:
                            break
        except Exception:
            pass
        return out

    def _strengthen(self, results: List[Dict[str, Any]]) -> None:
        ids = [r.get("id") for r in results if r.get("id")]
        if not ids:
            return
        try:
            with self._conn() as c:
                c.execute(
                    "UPDATE memories SET access_count=access_count+1,"
                    " strength=MIN(2.0, strength+0.2),"
                    " last_accessed_at=? WHERE id IN (%s)"
                    % ",".join("?" * len(ids)),
                    [time.time()] + ids)
        except Exception:
            pass

    # ==================================================================
    # Decay
    # ==================================================================

    def decay(self, periods: int = 1) -> int:
        n = 0
        with self._conn() as c:
            rows = c.execute("SELECT id, strength FROM memories").fetchall()
            for r in rows:
                new = max(self.DECAY_FLOOR, r["strength"] * (self.DECAY_RATE ** periods))
                if abs(new - r["strength"]) > 1e-6:
                    c.execute("UPDATE memories SET strength=? WHERE id=?", (new, r["id"]))
                    n += 1
        return n

    def profile(self, kind: str = "semantic", limit: int = 20,
                allowed_sensitivities: Sequence[str] = DEFAULT_SENSITIVITIES
                ) -> List[Dict[str, Any]]:
        """Widest first, under the same gate as :meth:`recall`.

        ``profile`` is the "what does this agent know" view. If it returned
        sensitive rows while ``recall`` did not, the gate would be cosmetic --
        one method away from leaking everything the other method protects.
        """
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM memories WHERE kind=? ORDER BY strength DESC, "
                "access_count DESC LIMIT ?", (kind, limit)).fetchall()
        return allowed_rows([dict(r) for r in rows], tuple(allowed_sensitivities or ()))

    def get(self, fact_id: str) -> Optional[Dict[str, Any]]:
        """Look up one memory by its id, across sensitivities.

        Deliberately ungated: knowing the id means the caller already has the
        fact. The gate is on retrieval by content, which is what turns "the
        agent remembered" into "the agent said it out loud".
        """
        with self._conn() as c:
            row = c.execute("SELECT * FROM memories WHERE id=?", (fact_id,)).fetchone()
        return dict(row) if row else None

    # ==================================================================
    # Symbolic offload (TencentDB pattern)
    # ==================================================================

    def offload(self, session_id: str, log_text: str, ref_dir: str) -> str:
        os.makedirs(ref_dir, exist_ok=True)
        ref_path = os.path.join(ref_dir, f"{session_id}.md")
        with open(ref_path, "w", encoding="utf-8") as fh:
            fh.write(log_text)
        return self.summarize(session_id, f"offloaded -> {ref_path}")

    # ==================================================================
    # Stats
    # ==================================================================

    def stats(self) -> Dict[str, Any]:
        with self._conn() as c:
            obs = c.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
            sem = c.execute("SELECT COUNT(*) FROM memories WHERE kind='semantic'").fetchone()[0]
            proc = c.execute("SELECT COUNT(*) FROM memories WHERE kind='procedural'").fetchone()[0]
            summ = c.execute("SELECT COUNT(*) FROM summaries").fetchone()[0]
            vec = c.execute("SELECT COUNT(*) FROM memories WHERE embedding IS NOT NULL").fetchone()[0]
        return {"observations": obs, "memories": sem + proc,
                "semantic": sem, "procedural": proc, "summaries": summ,
                "vector_embedded": vec,
                "vector_backend": self._vector_backend or "none"}