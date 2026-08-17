"""integrations/claude_code.py

MCP/CLAUDE-compatible bridge: how to connect NOESIS EventStore as
persistent memory for Claude Code sessions.

STATUS: STUB — contract only. Real MCP server requires external
network service (not available on this machine). This file defines
the local adapter contract + test harness.

Reference: https://github.com/anthropics/claude-code
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Contract: what a Claude Code session expects from a memory backend
# ---------------------------------------------------------------------------

class MemoryBackend:
    """
    Minimal interface a Claude Code session would call.
    Real implementation would be an MCP server; this is the local adapter.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init()

    def _conn(self):
        c = sqlite3.connect(self.db_path, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def _init(self):
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS claude_sessions (
                    session_id TEXT PRIMARY KEY,
                    project_path TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS claude_memories (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    scope TEXT NOT NULL,           -- 'project' | 'global' | 'transient'
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    accessed_at REAL NOT NULL
                )
            """)
            c.execute("""
                CREATE INDEX IF NOT EXISTS idx_claude_mem_session
                ON claude_memories(session_id)
            """)

    def get_session(self, project_path: str) -> str:
        """Get or create a session for a project."""
        import time
        with self._conn() as c:
            row = c.execute(
                "SELECT session_id FROM claude_sessions WHERE project_path=?",
                (project_path,)
            ).fetchone()
            if row:
                c.execute(
                    "UPDATE claude_sessions SET updated_at=? WHERE session_id=?",
                    (time.time(), row["session_id"])
                )
                return row["session_id"]
            sid = uuid.uuid4().hex
            c.execute(
                "INSERT INTO claude_sessions (session_id, project_path, created_at, updated_at) VALUES (?,?,?,?)",
                (sid, project_path, time.time(), time.time())
            )
            return sid

    def remember(self, session_id: str, scope: str, key: str, value: Any) -> str:
        """Store a memory (idempotent on session+scope+key)."""
        import time
        mid = uuid.uuid4().hex
        with self._conn() as c:
            # Upsert on (session_id, scope, key)
            c.execute("""
                INSERT INTO claude_memories (id, session_id, scope, key, value, created_at, accessed_at)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(session_id, scope, key) DO UPDATE SET
                    value=excluded.value, accessed_at=excluded.accessed_at
            """, (mid, session_id, scope, key, json.dumps(value, ensure_ascii=False), time.time(), time.time()))
        return mid

    def recall(self, session_id: str, scope: str, key: str) -> Optional[Any]:
        """Retrieve a memory by key."""
        with self._conn() as c:
            row = c.execute(
                "SELECT value FROM claude_memories WHERE session_id=? AND scope=? AND key=?",
                (session_id, scope, key)
            ).fetchone()
            if row:
                c.execute(
                    "UPDATE claude_memories SET accessed_at=? WHERE session_id=? AND scope=? AND key=?",
                    (time.time(), session_id, scope, key)
                )
                return json.loads(row["value"])
        return None

    def search(self, session_id: str, query: str, limit: int = 10) -> List[Dict]:
        """Full-text search across memories (simple LIKE for now)."""
        like = f"%{query}%"
        with self._conn() as c:
            rows = c.execute(
                "SELECT scope, key, value FROM claude_memories WHERE session_id=? AND value LIKE ? LIMIT ?",
                (session_id, like, limit)
            ).fetchall()
            return [{"scope": r["scope"], "key": r["key"], "value": json.loads(r["value"])} for r in rows]

    def list_keys(self, session_id: str, scope: str = "") -> List[str]:
        with self._conn() as c:
            if scope:
                rows = c.execute(
                    "SELECT key FROM claude_memories WHERE session_id=? AND scope=?", (session_id, scope)
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT key FROM claude_memories WHERE session_id=?", (session_id,)
                ).fetchall()
            return [r["key"] for r in rows]


# ---------------------------------------------------------------------------
# Local adapter using NOESIS EventStore + Memory (no external server needed)
# ---------------------------------------------------------------------------

class NoesisClaudeAdapter:
    """
    Wraps NOESIS EventStore + Memory to satisfy the MemoryBackend contract.
    This runs entirely locally — no MCP server, no network.
    """

    def __init__(self, state_dir: str):
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)

        # Import NOESIS core
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from noesis_harness import EventStore, Memory

        self.es = EventStore(os.path.join(state_dir, "claude_events.jsonl"))
        self.mem = Memory(os.path.join(state_dir, "claude_mem.db"))

    def get_session(self, project_path: str) -> str:
        """Get or create session, log to EventStore."""
        import hashlib
        sid = hashlib.sha256(project_path.encode()).hexdigest()[:16]
        self.es.append("claude_session_start", {"project_path": project_path, "session_id": sid})
        return sid

    def remember(self, session_id: str, scope: str, key: str, value: Any) -> str:
        """Store via NOESIS Memory (dedup + FTS5)."""
        kind = "semantic" if scope != "transient" else "procedural"
        fact = f"[{scope}] {key}: {json.dumps(value, ensure_ascii=False)}"
        mid = self.mem.save(fact, kind=kind, confidence=0.8)
        self.es.append("claude_remember", {"session_id": session_id, "scope": scope, "key": key})
        return mid

    def recall(self, session_id: str, scope: str, key: str) -> Optional[Any]:
        """Recall via NOESIS Memory (hybrid FTS5)."""
        results = self.mem.recall(key, limit=5, kind="semantic" if scope != "transient" else "procedural")
        for r in results:
            # Parse the stored fact format: "[scope] key: value"
            fact = r["fact"]
            if fact.startswith(f"[{scope}] {key}:"):
                try:
                    val_str = fact.split(":", 2)[2]
                    return json.loads(val_str)
                except Exception:
                    pass
        return None

    def search(self, session_id: str, query: str, limit: int = 10) -> List[Dict]:
        results = self.mem.recall(query, limit=limit)
        return [{"fact": r["fact"], "strength": r["strength"]} for r in results]


# ---------------------------------------------------------------------------
# Demo / self-test
# ---------------------------------------------------------------------------

def main():
    import tempfile
    import shutil

    tmp = tempfile.mkdtemp(prefix="claude_adapter_test_")
    try:
        print("Testing NoesisClaudeAdapter...")
        adapter = NoesisClaudeAdapter(tmp)

        # Simulate a Claude Code session
        project = "/home/user/my-project"
        sid = adapter.get_session(project)
        print(f"Session: {sid}")

        # Remember some facts
        adapter.remember(sid, "project", "language", "python")
        adapter.remember(sid, "project", "framework", "fastapi")
        adapter.remember(sid, "global", "preferred_editor", "vim")

        # Recall
        lang = adapter.recall(sid, "project", "language")
        print(f"Recalled language: {lang}")

        # Search
        results = adapter.search(sid, "python")
        print(f"Search 'python': {len(results)} results")

        print("\n[OK] Adapter test passed!")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()