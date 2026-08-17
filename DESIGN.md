# Design

This document explains the design decisions behind NOESIS-Harness-Agent-Memory.
Read it before making architecture-level changes.

## Problem

Long-running agents have three hard failure modes:

1. **State loss** - a crash loses in-memory state; decisions cannot be audited.
2. **Forgetting** - an agent that talked to a client yesterday does not
   remember what was said, and asks the same question again.
3. **Overlap** - two workers process the same lead at the same time, or two
   agents spin in an endless ping-pong loop.

## Design decisions

### D1. State is a replay of events, not a mutable store

Every decision is an append-only event. The current state is the fold of all
events through reducers. This gives us:

- **Crash safety** - a partial write loses only the last line.
- **Audit** - "why did the bot reply X?" = replay the candidate's event chain.
- **Idempotency** - a double-send with the same fingerprint is a no-op.

Source patterns: LoopX `event_sourced_state.py`, deepseek-harness `Session.append`.

### D2. Memory is four tiers, not one blob

| Tier | Table | Purpose | Lifecycle |
|------|-------|---------|-----------|
| Working | `observations` | raw inbound per session | bounded, per session |
| Episodic | `summaries` | "what happened" | per session |
| Semantic | `memories` (kind=semantic) | "what I know" (facts) | decay (Ebbinghaus) |
| Procedural | `memories` (kind=procedural) | "how to do it" (workflows) | decay + trigger |

Hybrid search: FTS5 BM25 first, substring fallback for CJK, strength ranking.
Symbolic offload (TencentDB): long logs to `refs/*.md`, agent keeps a pointer.

### D3. Coordination without a leader

No central dispatcher. Three primitives:

- **Leases** - exclusive TTL ownership of a task ("one task = one agent").
  A crashed holder's lease expires; work is reclaimed.
- **Signals** - async mailbox (broadcast, threads, read receipts).
- **Actions** - task DAG with typed edges (`requires`, `unlocks`, ...) and
  auto-unblock propagation on completion.

Source patterns: agentmemory `leases.ts`/`signals.ts`/`actions.ts`,
LoopX `task_lease.py`/`claim_visibility.py`.

### D4. Zero dependencies is a feature

The core is ~15 KB of stdlib Python. No pip install, no venv, no docker, no
node_modules. Clone -> run. This is the "local-first, no cloud, no API keys"
niche that the cloud-focused frameworks (Hermes, OpenClaw, MetaGPT) cannot serve.

### D5. Deterministic core, LLM optional

Storage, recall, and coordination never call an LLM. Compression and
summarization are pluggable callbacks the user injects. This keeps the core
testable (15+ stdlib tests) and free to run anywhere.

### D6. Fail-soft everywhere

A locked DB, a missing module, a corrupt tail line - each degrades to a no-op
with a logged warning. The framework must be the most stable process in a
multi-agent system (it is the one that restarts the others).

## Non-goals

- Vector search with embeddings (pluggable callback; brute-force top-K noted).
- P2P sync of memory across machines (agentmemory `mesh.ts` pattern, future).
- Cloud deployment. Local-first is the point.
- A GUI. CLI first.

## Trade-offs

| Choice | Gain | Cost |
|--------|------|------|
| Append-only JSONL | crash-safe, auditable | file grows; replay is O(n) |
| FTS5 SQLite | zero-dep full-text | no BM25 tuning exposed |
| TTL leases | crash-reclaim | clock skew risk on multi-host |
| stdlib only | zero friction | no ORM, hand-written SQL |

## See also

- `docs/architecture.md` - system architecture + diagrams.
- `docs/why.md` - comparison with agentmemory, TencentDB, hermes, loopx.
- `docs/api.md` - full API reference.
- `../RESEARCH_DAIGEST.md` - the 16-system research digest.
