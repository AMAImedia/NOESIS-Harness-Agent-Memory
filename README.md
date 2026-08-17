# NOESIS Harness — Agent Memory

**Local-first agent kernel: agents that do not forget, loop, or step on each other — on a laptop, stdlib only.**

Zero cloud. Zero API keys. Zero pip deps. Python 3.9+.

Version **0.5.0**. Tests: `python -m unittest discover -s tests -q` (67). Recall bench: `python benchmarks/recall20.py` (20/20).

---

## Why this exists

Long-running agents fail the same four ways: crash loses state, memory is a chat log, workers collide, and loops burn budget. NOESIS is the smallest kernel that closes all four without a warehouse (no Neo4j, no VikingDB, no Docker).

Patterns come from LoopX, agentmemory, TencentDB, Hermes, agent-teams, evalscope, plus 2026 context DBs (OpenViking VFS/L0–L2, Cognee-style edges) implemented as stdlib interfaces.

Docs: [docs/why.md](docs/why.md) · [docs/architecture.md](docs/architecture.md) · [docs/api.md](docs/api.md) · [docs/PLAN_0.5_BEAT_2026.md](docs/PLAN_0.5_BEAT_2026.md)

---

## Install

```bash
git clone https://github.com/AMAImedia/NOESIS-Harness-Agent-Memory
cd NOESIS-Harness-Agent-Memory
python -m unittest discover -s tests -q
```

No `pip install` required. Optional later: `pip install -e .` (still zero runtime deps).

---

## Quick start

```python
from noesis_harness import (
    EventStore, Memory, Leases, DurableQueue, LoopGuard,
    HitlGate, Budget, PrivacyFilter,
)

es = EventStore("state/events.jsonl")
es.append("sold", {"amount": 100})

mem = Memory("state/mem.db", privacy=PrivacyFilter())
mem.save("Client X needs Spanish film dubbing", kind="semantic", confidence=0.9)
print(mem.recall("Spanish"))

leases = Leases("state/leases.db")
leases.acquire("lead-42", "worker-A")

q = DurableQueue("state/q.db")
q.enqueue({"job": "score", "lead": "42"})

drafts = HitlGate("state/hitl.db")
did = drafts.draft("hello")          # cannot send until approve
drafts.approve(did)
drafts.mark_sent(did)

Budget("state/budget.db").spend("reply-42", validated=True)
```

---

## What you get (0.5)

| Piece | Module | Job |
|---|---|---|
| Event log + replay | `event_store` | crash-safe audit |
| 4-tier memory + FTS5 + RRF | `memory` | remember across sessions |
| Leases / signals / actions | `coordination` | no overlapping workers |
| Privacy + snapshot LWW | `privacy`, `snapshot` | secrets stay out; peers merge |
| Mesh + inspect UI | `mesh`, `inspect_ui` | folder/HTTP sync; `noesis-inspect` |
| Queue + loop guard | `queue`, `loop_guard` | durable jobs; no spin |
| Graph / scope / budget / HITL | `graph`, `scope`, `budget`, `hitl` | edges, tenants, spend-after-validate, draft≠send |
| VFS L0/L1/L2 + session extract | `vfs`, `session` | progressive load; obs→facts |
| MCP stdio + judge | `mcp_stdio`, `trace` | local tools; hybrid eval |

LLM is optional (`Memory(..., compressor=fn)`). Core never calls a model.

---

## Layout

```
noesis_harness/     # kernel (stdlib)
tests/              # unittest, no pytest
examples/           # botfarm_lead, swarm, tiers, dag, full_runtime
integrations/       # Claude/Codex/OpenClaw local adapters + McpServer
benchmarks/         # memory_bench + recall20
docs/               # architecture, api, why, plan 0.5, recipes
```

---

## Commands

```bash
python -m unittest discover -s tests -q
python examples/full_runtime.py
python examples/botfarm_lead.py
python benchmarks/recall20.py
python -m noesis_harness.inspect_ui --mem state/mem.db --events state/events.jsonl
```

---

## Design rules

1. Local-first, 6 GB VRAM laptop.
2. Deterministic core; LLM is a callback.
3. State is a projection of an append-only log.
4. Idempotent writes. Illegal transitions fail closed (HITL, budget).
5. No parent-folder docs required to use this repo.

---

## License

MIT. See [LICENSE](LICENSE).
