# Plan 0.5 — beat 2026 memory harnesses (not more weight)

Date: 2026-08-14. Sources: this repo + `_research_2026-08` digest + live GitHub
(OpenViking 28k, Cognee 30k, EverOS, Memori, memsearch, Letta, LoCoMo/tau2).

## Honest status

Shipped 0.4 is already better than *local-first coordination kernels*
(LoopX/agentmemory slices): event log, 4-tier memory, RRF, privacy, mesh,
queue, loop-guard, judge, inspect. **59 tests, stdlib.**

It is **not** yet better than 2026 *context databases* on retrieval UX:

| Gap | Who has it | Why it matters |
|-----|------------|----------------|
| Knowledge graph (entity edges) | Cognee, semantica, m_flow | BM25 misses "X works at Y" |
| URI / VFS + L0/L1/L2 load | OpenViking | -34..91% tokens; grep-able context |
| MCP server (stdio) | Cognee, OpenViking, memU | How Claude/Codex actually attach |
| Agent/tenant scope | Cognee, plan §1.3 | Fail-closed isolation |
| Spend-after-validate | LoopX (our original plan) | Budget only after writeback |
| HITL as type, not flag | BotFarm lesson | Draft/approve is the product |
| Markdown-native files | EverOS, memsearch | Git-diffable memory |
| Session -> memory extract | OpenViking sessions | Auto long-term from a run |
| Public recall numbers | OpenViking LoCoMo 80%+ | Claim needs a number |
| Subagent isolation | Plan phase D | Director context stays small |

Do **not** copy their stacks (Neo4j, VikingDB, Docker, AGPL server).
Stay stdlib. Steal the *interface*, not the warehouse.

## 0.5 ship order (this repo only)

1. [x] Graph edges on memories (subject-predicate-object, walk+recall).
2. [x] `agent_id` / tenant scope on Memory (fail-closed).
3. [x] Token/action Budget: validate write then spend (LoopX).
4. [x] HITL gate type: `draft|approve|reject|sent`, never auto-send.
5. [x] Context VFS: `noesis://` + L0/L1/L2 views.
6. [x] Stdlib MCP stdio adapter (save/recall/queue/trace/hitl).
7. [x] Session extract: observations -> episodic + semantic, no LLM.
8. [x] 20-fact public recall bench (`benchmarks/recall20.py`, gate acc>=0.8).

## Non-goals (still)

Cloud, PyPI until you say so, node_modules, second vector DB.

## After 0.5

Phase D subagents + BotFarm wiring stay in `PLAN_NOESIS_AGENT_OS.md`.
GitHub publish still operator-gated.
