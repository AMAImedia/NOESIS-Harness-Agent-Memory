# NOESIS-Harness-Agent-Memory — Architecture

> **Version:** 0.5.0 · **Status:** 67 unittest + recall20 20/20 · **Dependencies:** stdlib only

---

## Overview

NOESIS-Harness-Agent-Memory is a **zero-dependency, local-first agent coordination framework** built from patterns extracted from 16+ production agent systems (LoopX, agentmemory, TencentDB-Agent-Memory, Hermes Agent, agent-teams, deepseek-harness, evalscope, and others).

**Design principle:** Deterministic core (storage, coordination, replay) with LLM as an optional pluggable layer. No network calls, no heavy deps, runs on a laptop with 6 GB VRAM.

---

## Core Modules

```
noesis_harness/   # event_store, memory, coordination + 0.5 modules
                  # privacy snapshot consolidate procedures mesh inspect
                  # trace queue loop_guard graph budget hitl scope vfs session mcp_stdio
                  # __init__.py public exports
```

---

## Module 1: Event Store (`event_store.py`)

**Pattern source:** LoopX `event_sourced_state.py`, deepseek-harness `Session.append`

### Design
- **Append-only JSONL** — one line per event, crash-safe (partial write = lose last line only)
- **Idempotent append** — content fingerprint (SHA-256 of type + canonical JSON) prevents duplicate writes
- **Deterministic projection** — state = fold(events) through registered reducers
- **Replay/debug/audit** — rebuild any state from the log; no hidden mutable state

### Event Schema
```json
{
  "event_id": "sha256-fingerprint-or-explicit",
  "type": "candidate_found | reply_drafted | reply_sent | budget_spent | ...",
  "payload": { ... },
  "seq": 42
}
```

### API
```python
es = EventStore("output/events.jsonl")
es.register_reducer("inc", lambda state, payload: (state or 0) + payload["n"])
es.append("inc", {"n": 1})                    # returns event_id
es.append("inc", {"n": 1})                    # idempotent, same id returned
es.project(0)                                 # → 2 (deterministic replay)
```

### Idempotency
- Explicit `event_id` provided → used directly
- No `event_id` → content fingerprint (type + canonical payload) used
- Double-send with same content = no-op (absorbed at write)

---

## Module 2: Memory (`memory.py`)

**Pattern source:** agentmemory (4 tiers), TencentDB-Agent-Memory (L0-L3 offload), Hermes Agent (SQLite FTS5)

### Four Tiers

| Tier | Table | Purpose | Retention |
|------|-------|---------|-----------|
| **Working** | `observations` | Raw inbound events per session | Bounded per session |
| **Episodic** | `summaries` | Session summaries ("what happened") | Per session |
| **Semantic** | `memories` (kind=semantic) | Durable facts ("client X wants Y") | Decay (Ebbinghaus) |
| **Procedural** | `memories` (kind=procedural) | Workflows ("how to handle dubbing lead") | Decay + trigger |

### Hybrid Search
1. **FTS5 (BM25)** — primary keyword match on `memories.fact`
2. **Substring fallback** — for terms FTS5 tokenizes poorly (CJK, camelCase)
3. **Strength/decay ranking** — accessed facts strengthen; Ebbinghaus decay `strength *= 0.9^periods` (floor 0.1)

### Symbolic Offload (TencentDB pattern)
Long session logs → `refs/<session_id>.md` on disk. Agent keeps only a pointer/summary in context. When detail needed, grep the ref by `node_id`. **��61% token savings** (per TencentDB benchmarks).

### API
```python
mem = Memory("output/mem.db")

# Working / Episodic
mem.observe("session-1", "inbound", "client needs Spanish dubbing")
mem.summarize("session-1", "client wants festival dubbing ES")

# Semantic / Procedural (dedup + strengthen)
mem.save("client prefers European Spanish", kind="semantic", confidence=0.9)
mem.save("always ask for reference audio before cloning", kind="procedural")

# Recall (hybrid FTS5 + substring, strengthens on access)
mem.recall("dubbing", limit=5)

# Decay (run periodically)
mem.decay(periods=1)

# Offload long log to disk
mem.offload("session-1", big_log_text, "refs/")
```

---

## Module 3: Coordination (`coordination.py`)

**Pattern source:** agentmemory (leases.ts, signals.ts, actions.ts), LoopX (task_lease.py, claim_visibility.py)

### 3.1 Leases — Exclusive Task Ownership
- **One task = one agent** — TTL-bounded lease prevents stranded work on crash
- **Acquire** → returns `{ok, holder, expires_at, renewed}`
- **Renew** → extend lease (only holder)
- **Release** → explicit hand-off
- **Cleanup** → reclaim expired leases (background job)
- Default TTL: 10 min, max 1 hour

```python
L = Leases("coordination.db", ttl=600)
claim = L.acquire("lead-42", "worker-1")   # {"ok": True, "holder": "worker-1", ...}
L.renew("lead-42", "worker-1")             # extend
L.release("lead-42", "worker-1")           # hand off
L.cleanup()                                # reclaim expired
```

### 3.2 Signals — Async Mailbox
- **Broadcast** (empty `to_agent`) or **directed** (`to_agent="worker"`)
- **Threads** via `reply_to` / `thread_id`
- **Read receipts** (`read_at` timestamp)
- **TTL sweep** (default 24h)

```python
S = Signals("coordination.db")
S.send("director", "new lead found", to_agent="worker", type_="task")
S.send("worker", "reply drafted", reply_to=thread_id, type_="result")
inbox = S.read("worker")                    # marks read_at
threads = S.threads()                       # list active threads
```

### 3.3 Actions — Task DAG with Auto-Unblock
- **Edge types:** `requires` | `unlocks` | `gated_by` | `conflicts_with` | `spawned_by`
- **Auto-unblock** — when an action completes, any blocked dependent whose `requires` are all met flips `blocked → pending`
- **Frontier** — unblocked actions ranked by priority then age

```python
A = Actions("coordination.db")
a = A.create("fetch candidate")
b = A.create("score candidate", requires=[a])
c = A.create("draft reply", requires=[b])

A.complete(a)                               # b unblocks automatically
A.next()                                    # highest-priority pending action
A.frontier(5)                               # top 5 ready actions
```

---

## Data Flow Diagram

```
��─────────────────��     append()      ��──────────────────��
│   Agent Work    │ ───────────────�� │   EventStore     │  (append-only JSONL)
│  (find/score/   │                   │  - idempotent    │
│   reply/close)  │                   │  - fingerprint   │
��────────��────────��                   └────────��─────────��
         │                                     │
         ��                                     ��
��─────────────────��                   ��──────────────────��
│    Memory       │                   │  Projection      │
│  (4 tiers +     │                   │  (replay →       │
│   FTS5 + decay) │                   │   current state) │
��────────��────────��                   └──────────────────��
         │
         ��
��─────────────────��
│  Coordination   │
│  - Leases       │  (one task = one agent)
│  - Signals      │  (async mailbox)
│  - Actions      │  (DAG + auto-unblock)
��─────────────────��
```

---

## Zero-Dependency Guarantee

| Dependency | Used For | Alternative |
|------------|----------|-------------|
| `sqlite3` | Memory, Coordination | stdlib |
| `hashlib` | Event fingerprinting | stdlib |
| `json` | Serialization | stdlib |
| `threading` | Locks | stdlib |
| `time` | TTL, timestamps | stdlib |
| `uuid` | IDs | stdlib |
| `os` | Paths, dirs | stdlib |

**No:** numpy, requests, pandas, pydantic, yaml, toml, click, rich, tqdm, or any third-party package.

---

## LLM Integration (Pluggable, Optional)

The core **never calls an LLM**. Compression/summarization are callbacks:

```python
def llm_compress(text: str) -> str:
    # Your LLM call here (local or remote)
    return summary

mem = Memory("mem.db", compressor=llm_compress)  # optional
```

---

## Comparison with Source Systems

| Feature | LoopX | agentmemory | TencentDB | Hermes | NOESIS |
|---------|-------|-------------|-----------|--------|--------|
| Event sourcing | �� | �� | �� | ��� | �� |
| 4-tier memory | ��� | �� | �� (L0-L3) | ��� (FTS5 only) | �� |
| Symbolic offload | ��� | ��� | �� (Mermaid) | ��� | �� |
| Leases + TTL | �� | �� | ��� | ��� | �� |
| Signals (mailbox) | ��� | �� | ��� | ��� | �� |
| Action DAG + unblock | ��� | �� | ��� | ��� | �� |
| Zero deps | ��� | ��� (iii-engine) | ��� | ��� | �� |
| Local-first (no cloud) | ��� | ��� | ��� | ��� | �� |
| VRAM-aware (6 GB) | ��� | ��� | ��� | ��� | �� (BotFarm) |

---

## Running the Example

```bash
cd NOESIS-Harness-Agent-Memory
python examples/botfarm_lead.py
```

Output:
```
lead-1: processed. recalled=True
lead-2: processed. recalled=True
lead-3: processed. recalled=True

--- state summary ---
events: 3
memory: {'observations': 3, 'memories': 6, 'summaries': 0}
actions: {'done': 3}
signals inbox (closer): 3
```

---

## Testing

```bash
python -m unittest discover -s tests -v
# 67 tests, all passing (stdlib unittest, no deps)
```
