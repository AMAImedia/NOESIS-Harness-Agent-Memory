# NOESIS-Harness-Agent-Memory documentation

This directory contains the technical documentation for the local-first NOESIS agent kernel.

| Document | Purpose |
|---|---|
| [`ARCHITECTURE_1.0_NEXTGEN.md`](ARCHITECTURE_1.0_NEXTGEN.md) | Architecture of run envelopes, capabilities, audit chains, durable fibers, evidence memory, coordination and bounded context. |
| [`EVALUATION_PROTOCOL.md`](EVALUATION_PROTOCOL.md) | Reproducible criteria for memory, coordination, security, coding tasks and release decisions. |
| [`IMPLEMENTATION_REPORT_2026-08.md`](IMPLEMENTATION_REPORT_2026-08.md) | Verified local implementation report and benchmark snapshot dated 2026-08-17. |
| [`PLAN_NOESIS_1.0_MASTER.md`](PLAN_NOESIS_1.0_MASTER.md) | Master implementation plan and phase gates. |
| [`api.md`](api.md) | Existing API notes for the core package. |
| [`architecture.md`](architecture.md) | Earlier architecture notes retained for historical context. |
| [`why.md`](why.md) | Motivation and design rationale. |
| [`recipes/`](recipes/) | Focused examples for DAG actions, event sourcing, human-in-the-loop governance, memory tiers and multi-agent work. |

The repository is currently maintained as a **local Git project**. Documentation is written for safe review before any future public publication; no GitHub push is implied by the presence of these files.

## Security boundary

The deterministic core is stdlib-only and does not execute model-generated Python in-process. It provides capability decisions, auditability, logical private scopes and fail-soft execution status. It does **not** claim to replace an operating-system sandbox, VM, container or hardened remote execution service. The execution ladder returns `unavailable` when such an adapter is not configured.

## Sources

The design references [Cloudflare OS](https://github.com/cloudflare/cloudflare-os) and [Project Think](https://blog.cloudflare.com/project-think/) for capability-based access, durable execution, sub-agent isolation, persistent sessions and execution ladders. NOESIS implements a local Python/SQLite interpretation of selected principles rather than copying or depending on the Cloudflare runtime.
