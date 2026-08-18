# Roadmap

> **Current source of truth:** [`docs/PLAN_NOESIS_1.0_MASTER.md`](docs/PLAN_NOESIS_1.0_MASTER.md). Russian supplemental localization: [`docs/locales/ru/PLAN_NOESIS_1.0_MASTER_RU.md`](docs/locales/ru/PLAN_NOESIS_1.0_MASTER_RU.md).
>
> The versioned milestones below are historical context. They are not a substitute for the status-driven 1.0 plan.

## Current verified position — 2026-08-18

NOESIS is a **local-first, provenance-aware and human-governed agent OS kernel with a verified Linux control plane**. The local Python 3.14-only suite, durable sessions/tasks, bounded multi-agent coordination, memory/provenance layer, human-governed learning promotion, SQLite/WAL administrative state, signed evidence and Cloudflare-style operator telemetry are locally implemented and tested.

The project does not yet claim a finished native Windows/macOS distribution, fully autonomous executable-skill activation, or superiority over Hermes, OpenCode, DeepSeek Harness or other systems. Those claims require matching native hosts, exact pinned external revisions, disposable environments, signed evidence and comparable A/B metrics.

## Next gate

The next local gate is **production learning lifecycle binding**: connect terminal task completion, runtime-owned policy, authenticated operator sessions, independent reviewer authorization and the real proposal executor into one explicit workflow. Activation remains a separate approval-gated operation.

After that, the roadmap proceeds through governed executable child runtime, end-to-end multi-agent work-product execution, memory/long-context quality benchmarks, native Windows/macOS evidence, pinned external A/B and release-claim review.

Status legend for the historical section: `[x]` done, `[~]` in progress, `[ ]` planned.

## 0.2.x - Framework hardening

- [x] Core: EventStore, Memory (4 tiers), Coordination (leases/signals/actions).
- [x] Docs: architecture, api, why.
- [x] Examples: swarm, memory tiers, DAG, lead loop.
- [x] Integrations: Claude Code, Codex, OpenClaw (local adapters).
- [x] Benchmarks: EventStore + Memory, multi-size runner.
- [x] CI: tests 3.9-3.12, examples, benchmarks, build, lint.

## 0.3.x - Deeper memory

- [x] Vector tier (pluggable local embeddings; brute-force top-K).
- [x] RRF fusion weights configurable (0.4/0.6 like agentmemory).
- [x] Procedural workflow runner (trigger -> action matching + execution).
- [x] Memory consolidation worker as a first-class module.
- [x] Pluggable LLM compressor callback (`Memory(..., compressor=fn)`).

## 0.4.x - Multi-host

- [x] Git-snapshot memory export/import (agentmemory `snapshot.ts` pattern).
- [x] LWW merge for P2P sync (agentmemory `mesh.ts` pattern).
- [x] Privacy filter (regex registry before write; `privacy.ts` pattern).

## 0.5.x - Beat 2026 context DBs (stdlib interfaces)

See `docs/PLAN_0.5_BEAT_2026.md`.

- [x] Knowledge graph edges (`MemoryGraph`).
- [x] Agent/tenant scope (`ScopedMemory`).
- [x] Spend-after-validate (`Budget`).
- [x] HITL typed gate (`HitlGate`).
- [x] Context VFS `noesis://` + L0/L1/L2.
- [x] Stdlib MCP stdio adapter.
- [x] Session extract (obs -> semantic/episodic).
- [x] 20-fact public recall bench JSON.

## 1.0.0 - Release

- [x] 50+ tests, coverage gate >= 80%.
- [x] All examples runnable in < 10 min from clone on a laptop (6 GB VRAM).
- [x] Package publish-ready (`0.4.0`, `noesis-inspect` entry point). Twine upload needs operator token.
- [ ] `noesis-agent-os` meta-repo: this core + BotFarm as the app layer.

## Shipped (was ideas)

- [x] AgentTrace + hybrid judge (evalscope pattern).
- [x] Local inspect UI (`InspectUI` / `noesis-inspect`).
- [x] Folder + HTTP mesh sync (LWW, no cloud vendor).
- [x] Skills via procedural runner (Hermes trigger pattern).

## Non-goals

- Cloud deployment (local-first is the point).
- A heavy monolith (zero-dependency is the point).

## NOESIS 1.0 local-only track
See `docs/PLAN_NOESIS_1.0_MASTER.md` and `docs/ARCHITECTURE_1.0_NEXTGEN.md`.
- [x] Capability manifests, audit-chain integrity, idempotency, agent isolation, context tree, gatekeeper, DAG, vault and staged skills foundations.
- [ ] Durable fibers/checkpoints, full evidence-ranked consolidation, hardened execution adapters and adversarial evaluation.
