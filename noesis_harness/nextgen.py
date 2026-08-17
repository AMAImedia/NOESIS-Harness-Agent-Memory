"""NOESIS next-generation local primitives.

Stdlib-only, fail-closed building blocks for durable runs, capability security,
non-overlapping agents, proposals, and long-context sessions.  This module is
intentionally independent of the existing 0.5 API so the first iteration is
backwards-compatible.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple


class _ManagedConnection(sqlite3.Connection):
    """Commit/rollback plus close on context exit; required for Windows file cleanup."""

    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical_json(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class RunEnvelope:
    run_id: str
    agent_id: str
    task_id: str
    tenant_id: str = "local"
    parent_run_id: str = ""
    trace_id: str = ""
    policy_version: str = "1"
    capability_digest: str = ""
    created_at: float = field(default_factory=time.time)

    @classmethod
    def create(cls, agent_id: str, task_id: str, **kwargs: Any) -> "RunEnvelope":
        return cls(run_id=uuid.uuid4().hex, agent_id=agent_id, task_id=task_id,
                   trace_id=uuid.uuid4().hex, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityManifest:
    """Deny-by-default capability contract; never infer access from a path."""

    operations: Tuple[str, ...] = ()
    filesystem_roots: Tuple[str, ...] = ()
    network_hosts: Tuple[str, ...] = ()
    max_children: int = 0
    allow_secrets: bool = False
    version: str = "1"

    def digest(self) -> str:
        return sha256_hex(asdict(self))

    def allows(self, operation: str, target: str = "") -> bool:
        if operation not in self.operations:
            return False
        if operation in {"fs_read", "fs_write", "fs_delete"}:
            if not target:
                return False
            candidate = Path(target).expanduser().resolve()
            for root in self.filesystem_roots:
                try:
                    candidate.relative_to(Path(root).expanduser().resolve())
                    return True
                except ValueError:
                    continue
            return False
        if operation in {"net_read", "net_write"}:
            host = target.split("/", 1)[0].split(":", 1)[0].lower()
            return bool(host) and host in {h.lower() for h in self.network_hosts}
        if operation == "secret_use":
            return self.allow_secrets
        return operation in self.operations


class CapabilityDenied(PermissionError):
    pass


class AuditChain:
    """Append-only JSONL audit chain with deterministic verification."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _last_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        last = ""
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    last = line
        if not last:
            return "0" * 64
        return json.loads(last)["event_hash"]

    def append(self, actor: str, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            event = {
                "seq": self._next_seq(),
                "ts": time.time(),
                "actor": actor,
                "event_type": event_type,
                "payload": payload,
                "prev_hash": self._last_hash(),
            }
            event["event_hash"] = sha256_hex(event)
            with self.path.open("a", encoding="utf-8", newline="\n") as fh:
                fh.write(canonical_json(event) + "\n")
            return event

    def _next_seq(self) -> int:
        if not self.path.exists():
            return 1
        seq = 0
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    seq = int(json.loads(line)["seq"])
        return seq + 1

    def verify(self) -> Dict[str, Any]:
        with self._lock:
            previous = "0" * 64
            expected_seq = 1
            count = 0
            try:
                if not self.path.exists():
                    return {"ok": True, "events": 0, "last_hash": previous}
                with self.path.open("r", encoding="utf-8") as fh:
                    for line_no, line in enumerate(fh, 1):
                        if not line.strip():
                            continue
                        event = json.loads(line)
                        supplied = event.pop("event_hash", "")
                        if event.get("seq") != expected_seq or event.get("prev_hash") != previous:
                            return {"ok": False, "line": line_no, "reason": "sequence_or_link"}
                        if sha256_hex(event) != supplied:
                            return {"ok": False, "line": line_no, "reason": "hash_mismatch"}
                        event["event_hash"] = supplied
                        previous = supplied
                        expected_seq += 1
                        count += 1
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                return {"ok": False, "reason": type(exc).__name__}
            return {"ok": True, "events": count, "last_hash": previous}


class DurableCommandLedger:
    """SQLite idempotency ledger: a command id can produce one committed result."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.RLock()
        with self._conn() as db:
            db.execute("PRAGMA busy_timeout=5000")
            db.execute("CREATE TABLE IF NOT EXISTS commands (command_id TEXT PRIMARY KEY, result TEXT NOT NULL, created_at REAL NOT NULL)")

    def _conn(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path, timeout=5, factory=_ManagedConnection)
        db.row_factory = sqlite3.Row
        return db

    def execute_once(self, command_id: str, fn: Callable[[], Any]) -> Tuple[Any, bool]:
        if not command_id or not callable(fn):
            raise ValueError("command_id and callable are required")
        with self._lock, self._conn() as db:
            row = db.execute("SELECT result FROM commands WHERE command_id=?", (command_id,)).fetchone()
            if row is not None:
                return json.loads(row["result"]), False
            result = fn()
            encoded = canonical_json(result)
            db.execute("INSERT INTO commands(command_id,result,created_at) VALUES(?,?,?)",
                       (command_id, encoded, time.time()))
            return result, True


@dataclass(frozen=True)
class AgentManifest:
    agent_id: str
    role: str
    tenant_id: str = "local"
    parent_id: str = ""
    private_scope: str = ""
    readable_scopes: Tuple[str, ...] = ()
    writable_scopes: Tuple[str, ...] = ()
    max_children: int = 0
    context_budget: int = 8000
    capability_digest: str = ""

    def can_read(self, scope: str) -> bool:
        return scope == self.private_scope or scope in self.readable_scopes

    def can_write(self, scope: str) -> bool:
        return scope == self.private_scope or scope in self.writable_scopes


@dataclass(frozen=True)
class ResultEnvelope:
    task_id: str
    agent_id: str
    status: str
    output: Any
    evidence_ids: Tuple[str, ...] = ()
    uncertainty: float = 1.0
    proposed_memory_ids: Tuple[str, ...] = ()
    side_effects: Tuple[Dict[str, Any], ...] = ()


class IsolationBroker:
    """Explicit message/proposal broker; private scopes never leak implicitly."""

    def __init__(self, db_path: str, audit: Optional[AuditChain] = None):
        self.db_path = db_path
        self.audit = audit
        self._lock = threading.RLock()
        with self._conn() as db:
            db.execute("PRAGMA busy_timeout=5000")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS agents(agent_id TEXT PRIMARY KEY, manifest TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, sender TEXT NOT NULL, recipient TEXT NOT NULL, task_id TEXT NOT NULL, payload TEXT NOT NULL, created_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY, sender TEXT NOT NULL, recipient TEXT NOT NULL, scope TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, created_at REAL NOT NULL)
            """)

    def _conn(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path, timeout=5, factory=_ManagedConnection)
        db.row_factory = sqlite3.Row
        return db

    def register(self, manifest: AgentManifest) -> None:
        if not manifest.agent_id or not manifest.private_scope:
            raise ValueError("agent_id and private_scope are required")
        with self._lock, self._conn() as db:
            db.execute("INSERT OR REPLACE INTO agents(agent_id,manifest) VALUES(?,?)",
                       (manifest.agent_id, canonical_json(asdict(manifest))))

    def _get(self, agent_id: str) -> AgentManifest:
        with self._conn() as db:
            row = db.execute("SELECT manifest FROM agents WHERE agent_id=?", (agent_id,)).fetchone()
        if row is None:
            raise CapabilityDenied("unknown agent")
        return AgentManifest(**json.loads(row["manifest"]))

    def send(self, sender: str, recipient: str, task_id: str, payload: Dict[str, Any]) -> str:
        source = self._get(sender); self._get(recipient)
        if source.tenant_id != self._get(recipient).tenant_id:
            raise CapabilityDenied("cross-tenant message")
        mid = uuid.uuid4().hex
        with self._lock, self._conn() as db:
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)",
                       (mid, sender, recipient, task_id, canonical_json(payload), time.time()))
        if self.audit:
            self.audit.append(sender, "message_sent", {"message_id": mid, "recipient": recipient, "task_id": task_id})
        return mid

    def receive(self, recipient: str, limit: int = 100) -> List[Dict[str, Any]]:
        self._get(recipient)
        with self._conn() as db:
            rows = db.execute("SELECT * FROM messages WHERE recipient=? ORDER BY created_at LIMIT ?", (recipient, limit)).fetchall()
        return [{"id": r["id"], "sender": r["sender"], "recipient": r["recipient"], "task_id": r["task_id"], "payload": json.loads(r["payload"]), "created_at": r["created_at"]} for r in rows]

    def propose_memory(self, sender: str, recipient: str, scope: str, payload: Dict[str, Any]) -> str:
        source = self._get(sender); target = self._get(recipient)
        if source.tenant_id != target.tenant_id or not target.can_write(scope) or (scope == target.private_scope and source.agent_id != target.agent_id):
            raise CapabilityDenied("recipient cannot write proposed scope")
        pid = uuid.uuid4().hex
        with self._lock, self._conn() as db:
            db.execute("INSERT INTO proposals VALUES(?,?,?,?,?,?,?)",
                       (pid, sender, recipient, scope, canonical_json(payload), "pending", time.time()))
        if self.audit:
            self.audit.append(sender, "memory_proposed", {"proposal_id": pid, "recipient": recipient, "scope": scope})
        return pid

    def list_proposals(self, recipient: str, status: str = "pending") -> List[Dict[str, Any]]:
        self._get(recipient)
        with self._conn() as db:
            rows = db.execute("SELECT * FROM proposals WHERE recipient=? AND status=? ORDER BY created_at", (recipient, status)).fetchall()
        return [{"id": r["id"], "sender": r["sender"], "recipient": r["recipient"], "scope": r["scope"], "payload": json.loads(r["payload"]), "status": r["status"]} for r in rows]

    def decide_proposal(self, recipient: str, proposal_id: str, approve: bool) -> bool:
        self._get(recipient)
        status = "approved" if approve else "rejected"
        with self._lock, self._conn() as db:
            cur = db.execute("UPDATE proposals SET status=? WHERE id=? AND recipient=? AND status='pending'", (status, proposal_id, recipient))
            changed = cur.rowcount == 1
        if changed and self.audit:
            self.audit.append(recipient, "memory_proposal_decided", {"proposal_id": proposal_id, "status": status})
        return changed


@dataclass(frozen=True)
class MessageNode:
    id: str
    session_id: str
    parent_id: str
    role: str
    content: str
    created_at: float
    branch: str = "main"
    kind: str = "message"
    source_ids: Tuple[str, ...] = ()


class ContextManager:
    """Durable message tree with non-destructive compaction and budgeted packing."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.RLock()
        with self._conn() as db:
            db.execute("PRAGMA busy_timeout=5000")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, created_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, session_id TEXT NOT NULL, parent_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at REAL NOT NULL, branch TEXT NOT NULL, kind TEXT NOT NULL, source_ids TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS context_blocks(agent_id TEXT NOT NULL, name TEXT NOT NULL, content TEXT NOT NULL, budget INTEGER NOT NULL, updated_at REAL NOT NULL, PRIMARY KEY(agent_id,name))
            """)

    def _conn(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path, timeout=5, factory=_ManagedConnection)
        db.row_factory = sqlite3.Row
        return db

    def create_session(self, agent_id: str, session_id: str = "") -> str:
        sid = session_id or uuid.uuid4().hex
        with self._lock, self._conn() as db:
            db.execute("INSERT OR IGNORE INTO sessions VALUES(?,?,?)", (sid, agent_id, time.time()))
        return sid

    def add(self, session_id: str, role: str, content: str, parent_id: str = "", branch: str = "main", kind: str = "message", source_ids: Sequence[str] = ()) -> MessageNode:
        if not content or not role:
            raise ValueError("role and content are required")
        self.create_session("unknown", session_id)
        node = MessageNode(uuid.uuid4().hex, session_id, parent_id, role, content, time.time(), branch, kind, tuple(source_ids))
        with self._lock, self._conn() as db:
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?)", (node.id,node.session_id,node.parent_id,node.role,node.content,node.created_at,node.branch,node.kind,canonical_json(list(node.source_ids))))
        return node

    def fork(self, session_id: str, parent_id: str, branch: str) -> str:
        if not branch or not re.fullmatch(r"[A-Za-z0-9_.-]+", branch):
            raise ValueError("invalid branch")
        new_id = self.create_session("fork", uuid.uuid4().hex)
        # Preserve history by copying references as fork markers, never deleting original nodes.
        self.add(new_id, "system", "fork", parent_id=parent_id, branch=branch, kind="fork")
        return new_id

    def lineage(self, session_id: str, leaf_id: str = "") -> List[MessageNode]:
        with self._conn() as db:
            rows = db.execute("SELECT * FROM messages WHERE session_id=? ORDER BY created_at", (session_id,)).fetchall()
        nodes = {r["id"]: MessageNode(r["id"],r["session_id"],r["parent_id"],r["role"],r["content"],r["created_at"],r["branch"],r["kind"],tuple(json.loads(r["source_ids"]))) for r in rows}
        if not leaf_id:
            return list(sorted(nodes.values(), key=lambda n:n.created_at))
        out=[]; cur=leaf_id; seen=set()
        while cur and cur in nodes and cur not in seen:
            seen.add(cur); node=nodes[cur]; out.append(node); cur=node.parent_id
        return list(reversed(out))

    def compact(self, session_id: str, parent_id: str, summary: str, covered_ids: Sequence[str], branch: str = "main") -> MessageNode:
        if not summary or not covered_ids:
            raise ValueError("summary and covered_ids are required")
        return self.add(session_id, "system", summary, parent_id=parent_id, branch=branch, kind="compaction", source_ids=covered_ids)

    def set_block(self, agent_id: str, name: str, content: str, budget: int) -> None:
        if not name or budget < 1 or len(content) > budget:
            raise ValueError("invalid context block or budget exceeded")
        with self._lock, self._conn() as db:
            db.execute("INSERT OR REPLACE INTO context_blocks VALUES(?,?,?,?,?)", (agent_id,name,content,budget,time.time()))

    def pack(self, session_id: str, max_chars: int, agent_id: str = "", include_kinds: Sequence[str] = ("message", "compaction")) -> Dict[str, Any]:
        if max_chars < 1:
            raise ValueError("max_chars must be positive")
        parts=[]; used=0; selected=[]
        if agent_id:
            with self._conn() as db:
                blocks=db.execute("SELECT name,content,budget FROM context_blocks WHERE agent_id=? ORDER BY name", (agent_id,)).fetchall()
            for row in blocks:
                text=f"[{row['name']}]\n{row['content']}"
                if used + len(text) > max_chars: break
                parts.append(text); used += len(text); selected.append({"type":"block","name":row["name"]})
        nodes=self.lineage(session_id)
        for node in reversed(nodes):
            if node.kind not in include_kinds: continue
            text=f"{node.role}: {node.content}"
            if used + len(text) > max_chars: continue
            parts.append(text); used += len(text); selected.append({"type":"message","id":node.id,"source_ids":list(node.source_ids)})
        parts.reverse(); selected.reverse()
        return {"text":"\n\n".join(parts), "used_chars":used, "budget":max_chars, "selected":selected}


__all__ = [
    "canonical_json", "sha256_hex", "RunEnvelope", "CapabilityManifest", "CapabilityDenied",
    "AuditChain", "DurableCommandLedger", "AgentManifest", "ResultEnvelope", "IsolationBroker",
    "MessageNode", "ContextManager",
]
