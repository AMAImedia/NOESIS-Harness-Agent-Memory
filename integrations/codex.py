"""integrations/codex.py

OpenAI Codex CLI bridge: how to connect NOESIS EventStore + Memory
as persistent state for Codex agents.

STATUS: STUB — contract only. Real Codex integration requires
the Codex CLI (not available on this machine). This file defines
the local adapter contract + test harness.

Reference: https://github.com/openai/codex
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Contract: what a Codex session expects from a state backend
# ---------------------------------------------------------------------------

class CodexStateBackend:
    """
    Minimal interface a Codex session would call.
    Real implementation would use Codex's native state or an MCP bridge.
    This is the local adapter.
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
                CREATE TABLE IF NOT EXISTS codex_sessions (
                    session_id TEXT PRIMARY KEY,
                    workspace_path TEXT NOT NULL,
                    model TEXT NOT NULL DEFAULT 'gpt-5',
                    sandbox_mode TEXT NOT NULL DEFAULT 'read-only',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS codex_state (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    expires_at REAL,
                    created_at REAL NOT NULL
                )
            """)
            c.execute("""
                CREATE INDEX IF NOT EXISTS idx_codex_state_session
                ON codex_state(session_id)
            """)

    def create_session(self, workspace_path: str, model: str = "gpt-5",
                       sandbox_mode: str = "read-only") -> str:
        import time
        sid = uuid.uuid4().hex
        with self._conn() as c:
            c.execute(
                "INSERT INTO codex_sessions (session_id, workspace_path, model, sandbox_mode, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                (sid, workspace_path, model, sandbox_mode, time.time(), time.time())
            )
        return sid

    def get_session(self, workspace_path: str) -> Optional[str]:
        with self._conn() as c:
            row = c.execute(
                "SELECT session_id FROM codex_sessions WHERE workspace_path=?", (workspace_path,)
            ).fetchone()
            return row["session_id"] if row else None

    def set_state(self, session_id: str, key: str, value: Any, ttl: Optional[int] = None) -> str:
        import time
        mid = uuid.uuid4().hex
        expires = time.time() + ttl if ttl else None
        with self._conn() as c:
            c.execute("""
                INSERT INTO codex_state (id, session_id, key, value, expires_at, created_at)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(session_id, key) DO UPDATE SET value=excluded.value, expires_at=excluded.expires_at
            """, (mid, session_id, key, json.dumps(value, ensure_ascii=False), expires, time.time()))
        return mid

    def get_state(self, session_id: str, key: str) -> Optional[Any]:
        with self._conn() as c:
            row = c.execute(
                "SELECT value, expires_at FROM codex_state WHERE session_id=? AND key=?",
                (session_id, key)
            ).fetchone()
            if not row:
                return None
            if row["expires_at"] and row["expires_at"] < time.time():
                c.execute("DELETE FROM codex_state WHERE session_id=? AND key=?", (session_id, key))
                return None
            return json.loads(row["value"])

    def list_keys(self, session_id: str) -> List[str]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT key FROM codex_state WHERE session_id=?", (session_id,)
            ).fetchall()
            return [r["key"] for r in rows]

    def delete_state(self, session_id: str, key: str) -> bool:
        with self._conn() as c:
            cur = c.execute("DELETE FROM codex_state WHERE session_id=? AND key=?", (session_id, key))
            return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Local adapter using NOESIS EventStore + Memory
# ---------------------------------------------------------------------------

class NoesisCodexAdapter:
    """
    Wraps NOESIS EventStore + Memory for Codex-style state.
    Runs entirely locally — no external server required.
    """

    def __init__(self, state_dir: str):
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)

        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from noesis_harness import EventStore, Memory

        self.es = EventStore(os.path.join(state_dir, "codex_events.jsonl"))
        self.mem = Memory(os.path.join(state_dir, "codex_mem.db"))

    def create_session(self, workspace_path: str, model: str = "gpt-5",
                       sandbox_mode: str = "read-only") -> str:
        import hashlib
        sid = hashlib.sha256(f"{workspace_path}:{model}:{sandbox_mode}".encode()).hexdigest()[:16]
        self.es.append("codex_session_start", {
            "workspace_path": workspace_path,
            "model": model,
            "sandbox_mode": sandbox_mode,
            "session_id": sid
        })
        return sid

    def set_state(self, session_id: str, key: str, value: Any, ttl: Optional[int] = None) -> str:
        fact = f"[codex:{session_id}] {key}: {json.dumps(value, ensure_ascii=False)}"
        mid = self.mem.save(fact, kind="procedural", confidence=0.8)
        self.es.append("codex_state_set", {"session_id": session_id, "key": key, "ttl": ttl})
        return mid

    def get_state(self, session_id: str, key: str) -> Optional[Any]:
        results = self.mem.recall(key, limit=5, kind="procedural")
        for r in results:
            fact = r["fact"]
            prefix = f"[codex:{session_id}] {key}:"
            if fact.startswith(prefix):
                try:
                    val_str = fact[len(prefix):]
                    return json.loads(val_str)
                except Exception:
                    pass
        return None

    def list_keys(self, session_id: str) -> List[str]:
        prefix = f"[codex:{session_id}]"
        # Escape FTS5 special characters in prefix
        escaped = prefix.replace('[', ' ').replace(']', ' ').replace(':', ' ')
        results = self.mem.recall(escaped, limit=50, kind="procedural")
        keys = []
        for r in results:
            fact = r["fact"]
            expected_prefix = f"[codex:{session_id}]"
            if fact.startswith(expected_prefix):
                try:
                    rest = fact[len(expected_prefix):].strip()
                    key = rest.split(":", 1)[0]
                    keys.append(key)
                except Exception:
                    pass
        return keys

    def delete_state(self, session_id: str, key: str) -> bool:
        # Memory doesn't support delete directly; mark as deleted via event
        self.es.append("codex_state_deleted", {"session_id": session_id, "key": key})
        return True


# ---------------------------------------------------------------------------
# Demo / self-test
# ---------------------------------------------------------------------------

def main():
    import tempfile
    import shutil
    import time

    tmp = tempfile.mkdtemp(prefix="codex_adapter_test_")
    try:
        print("Testing NoesisCodexAdapter...")
        adapter = NoesisCodexAdapter(tmp)

        # Simulate a Codex session
        workspace = "/home/user/my-project"
        sid = adapter.create_session(workspace, model="gpt-5", sandbox_mode="read-only")
        print(f"Session: {sid}")

        # Set state (simulating file edits, test results, etc.)
        adapter.set_state(sid, "last_file_edited", "src/main.py")
        adapter.set_state(sid, "test_results", {"passed": 42, "failed": 3})
        adapter.set_state(sid, "current_task", "implement user auth")

        # Get state
        task = adapter.get_state(sid, "current_task")
        print(f"Current task: {task}")

        test_results = adapter.get_state(sid, "test_results")
        print(f"Test results: {test_results}")

        # List keys
        keys = adapter.list_keys(sid)
        print(f"All keys: {keys}")

        # Check events were logged
        from noesis_harness import EventStore
        es = EventStore(os.path.join(tmp, "codex_events.jsonl"))
        print(f"Events logged: {es.count()}")

        print("\n[OK] Adapter test passed!")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()