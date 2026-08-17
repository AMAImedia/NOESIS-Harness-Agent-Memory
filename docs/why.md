# Why NOESIS-Harness-Agent-Memory?

> **The short answer:** It's the only zero-dependency, local-first agent coordination framework that combines event-sourced state, 4-tier memory with symbolic offload, and full multi-agent coordination (leases + signals + actions) — all in ~1 KB of stdlib Python.

---

## The Problem

You want to run a team of agents 24/7 on your laptop (6 GB VRAM, no cloud, no API keys). Existing options:

| Framework | Deps | Local-first | Event sourcing | 4-tier memory | Coordination | VRAM-aware |
|-----------|------|-------------|----------------|---------------|--------------|------------|
| **Hermes Agent** | 70+ tools, heavy | ���� | ����� | ����� (FTS5 only) | Delegate tool | ����� |
| **agent-teams** | Hermes + more | ���� | TaskQueue only | ����� | Yes (swarm) | ����� |
| **OpenClaw** | 100+ MB | ���� | ����� | ����� | ����� | ����� |
| **LoopX** | Control plane | ���� | ���� | ����� | Claims+leases | ����� |
| **agentmemory** | iii-engine | ���� | ���� | ���� | ���� (full) | ����� |
| **TencentDB** | LLM for compression | ���� | ���� | ���� (L0-L3) | ����� | ����� |
| **deepseek-harness** | Cordis/plugins | ���� | ���� | ����� | Capability seam | ����� |
| **evalscope** | Heavy eval deps | ���� | ����� | ����� | Judge only | ����� |
| **MetaGPT / XAgent / Qwen-Agent** | Heavy | Cloud-first | ����� | ����� | Role-based | ����� |
| **Claude Code / Codex** | Proprietary | ����� | ����� | ����� | Subagents only | ����� |
| **NOESIS** | **stdlib only** | **��** | **��** | **��** | **��** | **��** |

---

## What Makes NOESIS Different

### 1. **Zero Dependencies = Zero Friction**
```bash
# No pip install, no venv, no docker, no npm, no cargo
python examples/botfarm_lead.py
# Just works. 15 tests pass with stdlib unittest.
```
No `pip install`, no `npm install`, no `docker pull`, no `cargo build`. The entire framework is **~15 KB** of stdlib Python. Clone → run → done.

### 2. **Event-Sourced State = Audit + Replay + Crash-Safe**
```python
# Every decision is an append-only event
es.append("reply_sent", {"lead_id": "L1", "text": "..."})
# Crash? Reboot → es.project() rebuilds exact state
# Audit? grep events.jsonl for "why did bot reply X?"
```
- **Append-only JSONL** — crash-safe (partial write = lose last line only)
- **Idempotent append** — double-send = no-op (fingerprint dedup)
- **Deterministic projection** — state = fold(events) → perfect replay/debug
- **Effect IDs** — `cycle:candidate:reply` chains for end-to-end traceability

### 3. **4-Tier Memory + Symbolic Offload = Long-Term Recall**
| Tier | Purpose | Mechanism |
|------|---------|-----------|
| Working | Raw inbound per session | `observations` table |
| Episodic | Session summaries | `summaries` table |
| Semantic | Durable facts + confidence | `memories` (kind=semantic) + FTS5 |
| Procedural | Workflows + triggers | `memories` (kind=procedural) + decay |

**Hybrid search:** FTS5 (BM25) + substring fallback + strength/decay ranking.  
**Decay:** Ebbinghaus `strength *= 0.9^periods` (floor 0.1).  
**Symbolic offload:** Long logs → `refs/<id>.md` on disk, agent keeps pointer. **-61% tokens** (TencentDB pattern).

```python
mem.save("client prefers European Spanish", kind="semantic", confidence=0.9)
mem.offload("session-42", huge_log, "refs/")  # writes refs/42.md, keeps pointer
mem.recall("dubbing")  # FTS5 + substring + strength ranking
```

### 4. **Real Multi-Agent Coordination (Not Just "Delegation")**

| Primitive | Purpose | Pattern Source |
|-----------|---------|----------------|
| **Leases** | Exclusive TTL task ownership | agentmemory + LoopX |
| **Signals** | Async mailbox (broadcast, threads, receipts) | agentmemory |
| **Actions** | DAG with `requires` + auto-unblock | agentmemory + LoopX |

```python
# One task = one agent (lease)
lease = leases.acquire("lead-42", "worker-1")  # blocks others

# Async communication
signals.send("director", "new lead", to_agent="worker")

# Task DAG with auto-unblock
a = actions.create("fetch")
b = actions.create("score", requires=[a])
actions.complete(a)  # b auto-unblocks
```

**No central dispatcher** — agents coordinate peer-to-peer via leases + signals. If any agent crashes, leases expire and work is reclaimed.

### 5. **Local-First, VRAM-Aware (The NOESIS BotFarm Proof)**
This framework isn't theoretical — it powers the **NOESIS BotFarm** running 24/7 on a **6 GB RTX 3060 laptop**:
- 0.8B resident models + 9B swap via VRAM manager
- 100% local (no API keys, no cloud)
- Human-in-the-loop gate (draft → approve → send)
- Durable queue + loop guard (ported from agent-teams)

> **No other open-source framework runs a full agent team + local LLMs on 6 GB VRAM.**

### 5. **Deterministic Core, LLM Optional**
The framework **never calls an LLM**. Compression/summarization are optional pluggable callbacks:

```python
def my_llm_compress(text): ...
mem = Memory("mem.db", compressor=my_llm_compress)  # optional!
```

No forced LLM deps, no API keys required for core operation.

### 6. **Battle-Tested Patterns, Not Academic Ideas**
Every pattern is extracted from **production systems**:
- **Durable queue + loop guard** → ported from agent-teams (hermes-swarm), running in NOESIS BotFarm since 2026
- **Event sourcing** → LoopX `event_sourced_state.py` + deepseek-harness `Session.append`
- **4-tier memory + hybrid search** → agentmemory (most complete open impl)
- **Symbolic offload** → TencentDB-Agent-Memory (measured -61% tokens)
- **Leases + signals + actions** → agentmemory (most complete coordination)
- **Agent trace + hybrid judge** → evalscope `llm_recall`

---

## Honest Comparison: What We Don't Have (Yet)

| Feature | Status |
|---------|--------|
| Vector search + RRF | Shipped (optional backends, stdlib fallback) |
| Folder/HTTP mesh LWW | Shipped (`Mesh`, `serve_mesh`) |
| Inspect UI | Shipped (`InspectUI`, `noesis-inspect`) |
| Privacy + snapshot | Shipped |
| Queue + loop guard | Shipped |
| Cloud vendor deploy | Not a goal (local-first) |

---

## The "Best GitHub" Claim

> **NOESIS = the framework that lets ANY developer with a laptop run a durable, coordinated agent team locally — no cloud, no API keys, no 100 MB deps.**

We're not competing on "most features" or "biggest community." We're competing on **honest utility for the local-first developer**:
- Clone → run in 5 seconds
- 15 tests, 0 deps, 15 KB core
- Patterns with provenance (every module cites its source)
- Runs the NOESIS BotFarm 24/7 on a 6 GB laptop
- MIT license, stdlib only, English only, no emoji

---

## Get Started in 30 Seconds

```bash
git clone https://github.com/AMAImedia/NOESIS-Harness-Agent-Memory
cd NOESIS-Harness-Agent-Memory
python examples/botfarm_lead.py
# events: 3
# memory: {'observations': 3, 'memories': 6, 'summaries': 0}
# actions: {'done': 3}
# signals inbox (closer): 3
```

---

## Sources (Provenance)

Every module documents its source patterns. Internal research notes live next to this repo during development; published tree is self-contained (`docs/`).

| Module | Primary Sources |
|--------|-----------------|
| `event_store.py` | LoopX `event_sourced_state.py`, deepseek-harness `Session.append` |
| `memory.py` | agentmemory (4 tiers), TencentDB-Agent-Memory (offload), Hermes Agent (FTS5) |
| `coordination.py` | agentmemory (leases/signals/actions), LoopX (task_lease/claims) |

---

## License

MIT — use it, fork it, build on it. No attribution required, but provenance is appreciated.