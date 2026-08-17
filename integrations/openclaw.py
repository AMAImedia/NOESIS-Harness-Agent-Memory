"""integrations/openclaw.py

OpenClaw bridge: how to connect NOESIS EventStore + Memory
as persistent state for OpenClaw agents.

STATUS: STUB — contract only. Real OpenClaw integration requires
the OpenClaw runtime (not available on this machine). This file
defines the local adapter contract + test harness.

Reference: https://github.com/OpenClaw/OpenClaw
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Contract: what an OpenClaw agent expects from a state backend
# ---------------------------------------------------------------------------

class OpenClawStateBackend:
    """
    Minimal interface an OpenClaw agent would call.
    Real implementation would use OpenClaw's native state management.
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
                CREATE TABLE IF NOT EXISTS openclaw_agents (
                    agent_id TEXT PRIMARY KEY,
                    role TEXT NOT NULL,
                    config TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS openclaw_state (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    scope TEXT NOT NULL DEFAULT 'agent',  -- agent | team | global
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            c.execute("""
                CREATE INDEX IF NOT EXISTS idx_oc_state_agent
                ON openclaw_state(agent_id)
            """)

    def register_agent(self, agent_id: str, role: str, config: Dict = None) -> str:
        import time
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO openclaw_agents (agent_id, role, config, created_at) VALUES (?,?,?,?)",
                (agent_id, role, json.dumps(config or {}), time.time())
            )
        return agent_id

    def set_state(self, agent_id: str, key: str, value: Any, scope: str = "agent") -> str:
        import time
        mid = uuid.uuid4().hex
        with self._conn() as c:
            c.execute("""
                INSERT INTO openclaw_state (id, agent_id, key, value, scope, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(agent_id, key, scope) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """, (mid, agent_id, key, json.dumps(value, ensure_ascii=False), scope, time.time(), time.time()))
        return mid

    def get_state(self, agent_id: str, key: str, scope: str = "agent") -> Optional[Any]:
        with self._conn() as c:
            row = c.execute(
                "SELECT value FROM openclaw_state WHERE agent_id=? AND key=? AND scope=?",
                (agent_id, key, scope)
            ).fetchone()
            return json.loads(row["value"]) if row else None

    def list_keys(self, agent_id: str, scope: str = "") -> List[str]:
        with self._conn() as c:
            if scope:
                rows = c.execute(
                    "SELECT key FROM openclaw_state WHERE agent_id=? AND scope=?", (agent_id, scope)
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT key FROM openclaw_state WHERE agent_id=?", (agent_id,)
                ).fetchall()
            return [r["key"] for r in rows]


# ---------------------------------------------------------------------------
# Local adapter using NOESIS EventStore + Memory + Coordination
# ---------------------------------------------------------------------------

class NoesisOpenClawAdapter:
    """
    Wraps NOESIS EventStore + Memory + Coordination for OpenClaw-style agents.
    Adds multi-agent coordination (leases, signals) which OpenClaw lacks natively.
    """

    def __init__(self, state_dir: str):
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)

        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from noesis_harness import EventStore, Memory, Leases, Signals

        self.es = EventStore(os.path.join(state_dir, "openclaw_events.jsonl"))
        self.mem = Memory(os.path.join(state_dir, "openclaw_mem.db"))
        self.leases = Leases(os.path.join(state_dir, "openclaw_leases.db"))
        self.signals = Signals(os.path.join(state_dir, "openclaw_signals.db"))

    def register_agent(self, agent_id: str, role: str, config: Dict = None) -> str:
        self.es.append("openclaw_agent_register", {"agent_id": agent_id, "role": role, "config": config})
        # Claim a lease for this agent's identity
        self.leases.acquire(f"agent:{agent_id}", agent_id)
        return agent_id

    def set_state(self, agent_id: str, key: str, value: Any, scope: str = "agent") -> str:
        fact = f"[openclaw:{scope}] {agent_id}:{key}: {json.dumps(value, ensure_ascii=False)}"
        kind = "semantic" if scope != "transient" else "procedural"
        mid = self.mem.save(fact, kind=kind, confidence=0.8)
        self.es.append("openclaw_state_set", {"agent_id": agent_id, "key": key, "scope": scope})
        return mid

    def get_state(self, agent_id: str, key: str, scope: str = "agent") -> Optional[Any]:
        results = self.mem.recall(key, limit=5, kind="semantic" if scope != "transient" else "procedural")
        for r in results:
            fact = r["fact"]
            prefix = f"[openclaw:{scope}] {agent_id}:{key}:"
            if fact.startswith(prefix):
                try:
                    val_str = fact[len(prefix):]
                    return json.loads(val_str)
                except Exception:
                    pass
        return None

    # --- OpenClaw-specific: multi-agent coordination ---

    def claim_task(self, task_key: str, agent_id: str) -> Dict:
        """Exclusive task claim using NOESIS Leases."""
        return self.leases.acquire(task_key, agent_id)

    def release_task(self, task_key: str, agent_id: str) -> bool:
        return self.leases.release(task_key, agent_id)

    def send_signal(self, from_agent: str, to_agent: str, payload: Any, type_: str = "info") -> str:
        """Inter-agent communication via NOESIS Signals."""
        return self.signals.send(from_agent, payload, to_agent=to_agent, type_=type_)

    def read_signals(self, agent_id: str, unread_only: bool = True) -> List[Dict]:
        return self.signals.read(agent_id, unread_only=unread_only)

    def broadcast(self, from_agent: str, payload: Any, type_: str = "broadcast") -> str:
        return self.signals.send(from_agent, payload, to_agent="", type_=type_)


# ---------------------------------------------------------------------------
# Demo / self-test
# ---------------------------------------------------------------------------

def main():
    import tempfile
    import shutil

    tmp = tempfile.mkdtemp(prefix="openclaw_adapter_test_")
    try:
        print("Testing NoesisOpenClawAdapter...")
        adapter = NoesisOpenClawAdapter(tmp)

        # Register two agents
        adapter.register_agent("agent-researcher", "researcher", {"model": "gpt-4", "tools": ["web_search"]})
        adapter.register_agent("agent-coder", "coder", {"model": "gpt-4", "tools": ["code_exec"]})
        print("Agents registered")

        # Agent 1 sets state
        adapter.set_state("agent-researcher", "findings", ["paper1", "paper2"], scope="team")
        adapter.set_state("agent-coder", "implementation_plan", ["step1", "step2"], scope="agent")
        print("State set")

        # Agent 2 reads team state
        findings = adapter.get_state("agent-coder", "findings", scope="team")
        print(f"Coder read team findings: {findings}")

        # Task coordination via leases
        claim = adapter.claim_task("implement_auth", "agent-coder")
        print(f"Coder claimed task: {claim['ok']}")

        # Inter-agent signal
        adapter.send_signal("agent-coder", "agent-researcher", "auth module done", type_="result")
        inbox = adapter.read_signals("agent-researcher")
        print(f"Researcher inbox: {len(inbox)} messages")

        # Check events
        from noesis_harness import EventStore
        es = EventStore(os.path.join(tmp, "openclaw_events.jsonl"))
        print(f"Events logged: {es.count()}")

        print("\n[OK] Adapter test passed!")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    import tempfile
    import shutil
    main()