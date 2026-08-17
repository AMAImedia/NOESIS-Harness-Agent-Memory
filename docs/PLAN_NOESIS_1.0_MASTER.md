# NOESIS-Harness-Agent-Memory 1.0 — проверенный план развития

Дата: 2026-08-16. Область: только локальная папка на ноутбуке `NOESIS-Harness-Agent-Memory`; работа ведётся без публикации в GitHub, публикация запрещена до отдельного решения владельца.

## 1. Цель и критерий честного улучшения

Цель — превратить существующее local-first ядро в изолированный multi-agent harness с доказуемой долговременной памятью, управлением длинным контекстом, возобновляемыми задачами, безопасной лестницей исполнения, человеко-контролируемым самоулучшением и Obsidian-подобной человекочитаемой базой знаний. Мы не будем считать увеличение числа таблиц, токенов или файлов улучшением. Каждая новая возможность должна иметь тест, измеримый benchmark и отказоустойчивое поведение.

Текущий baseline из локального плана 0.5: stdlib-only Python core, event store, четыре уровня памяти, FTS/RRF и optional vector callback, graph edges, agent/tenant scope, budgets, HITL draft/approve/reject/sent, context VFS L0/L1/L2, MCP stdio, session extraction, leases, queue, loop guard, judge и recall20 gate. Сохраняем обратную совместимость и не добавляем обязательные внешние зависимости.

## 2. Архитектурные принципы

| Принцип | Реализация | Запрещённая подмена |
|---|---|---|
| Deny by default | Capability manifest на агента, задачу, инструмент, путь, домен и side effect | Ambient tools, общий секрет, общий writable memory |
| Изоляция | Отдельный agent namespace/state, приватные memory scopes и брокер явных сообщений | Общая таблица фактов без scope и прямой writeback child → parent |
| Доказуемая память | Provenance, source event, confidence, freshness, conflict set, retrieval trace и benchmark | Простое добавление текста в MEMORY.md без проверки полезности |
| Длинный контекст | Message tree, fork, checkpoint, non-destructive compaction, L0–L3 retrieval | Потеря старой истории после summary |
| Durable execution | Идемпотентный task ledger, checkpoint/resume, TTL lease, retry budget | Надежда на in-memory loop |
| Безопасное самоулучшение | Proposal → diff → tests → review → apply, rollback и quarantine | Автоматическая запись кода или памяти без gate |
| Local-first | stdlib core; optional adapters для SQLite/Markdown/Windows sandbox/внешних embeddings | Обязательный cloud, vector DB или API key |
| Проверяемость | Hash-chain audit, deterministic replay, failure injection и leakage tests | Маркетинговое “safe” без adversarial tests |

## 3. Целевая система

### 3.1 Kernel и durable state

Добавить versioned schema migrations и единый `RunEnvelope`: `run_id`, `agent_id`, `parent_run_id`, `tenant_id`, `task_id`, `capability_digest`, `policy_version`, `created_at`, `trace_id`. Все переходы состояния проходят через append-only event log и идемпотентный, idempotent command handler. Сохранить WAL, busy timeout и fail-soft, но добавить hash-chain `prev_hash`/`event_hash`, sequence checks, snapshot manifest и replay validator. Любая corruption или gap должна останавливать доверенный replay и переходить в read-only/quarantine, а не тихо продолжать.

### 3.2 Durable sessions, branches и long context

Ввести message tree с parent IDs, branch IDs и monotonically increasing sequence. Реализовать fork, checkpoint, resume, cancel, retry и compaction records. Compaction только добавляет summary node с ссылками на исходный диапазон, digest, model/prompt version и coverage; оригиналы не удаляются. Context packer должен собирать окно из: system policy, role contract, pinned memory blocks, current branch, retrieved evidence, task state и tool results. Каждый блок имеет token/character budget и provenance. Retrieval должен возвращать evidence IDs, score, freshness и объяснимую причину попадания.

### 3.3 Память: четыре уровня плюс vault projection

Сохранить L0 pinned context, L1 session working set, L2 semantic/episodic/procedural memory и L3 cold archive/refs. Добавить типизированные memory blocks: `soul`, `user`, `project`, `task`, `policy`, `procedure`, `evidence`. У каждого блока owner, readers, writer policy, max budget, TTL/decay, confidence, source events и conflict status. Добавить deterministic consolidation: deduplicate, merge only with evidence, mark contradictions instead of overwriting, decay stale facts, and require explicit promotion from observation to durable fact.

Создать Markdown/Obsidian projection: one note per stable entity or decision, YAML frontmatter, stable IDs, typed wikilinks, backlinks/index, daily/session notes, source references and human edits imported as versioned events. Markdown — projection and review surface, not an unverified source of truth. Changes from vault pass through parser, injection scanner, provenance and approval policy.

### 3.4 Non-overlapping multi-agent model

Ввести `AgentManifest`: role, parent, private scopes, readable shared scopes, writable outputs, tool capabilities, context budget, model policy, max cost, expiration and allowed delegation. Child agents receive a minimal task contract and evidence bundle, not the parent transcript. Child private memory is never automatically merged. Return path is a typed `ResultEnvelope` with output, evidence IDs, claims, uncertainty, artifacts, proposed memories and side-effect requests.

Создать coordinator/broker with typed RPC over the existing queue/event primitives. Use leases and idempotency keys; reject duplicate or stale messages. Shared memory is a separate explicitly named scope with append-only proposals; parent accepts or rejects them. Cross-agent leakage tests must prove that a child cannot recall another child’s private facts, and that unapproved proposals do not appear in parent context.

### 3.5 Planning and execution

Добавить DAG task planner with dependencies, critical path, bounded parallelism, retries, cancellation, deadlines and result joins. A director agent plans and delegates; specialist agents research, code, test, review or summarize; a judge checks evidence and policy. The director does not inherit full specialist context. Every step has a budget and a stop condition, and the system must detect loops, deadlocks, starvation and over-delegation.

### 3.6 Cloudflare-OS-inspired execution ladder without fake sandbox claims

Reimplement interfaces, not a copy of Cloudflare code. Tier 0 is current VFS/read/search/edit/diff with transaction plans. Tier 1 is a capability-scoped code plan that is only simulated by default; a future Dynamic Worker adapter is optional and must not be described as a security boundary unless the runtime proves it. Tier 2 is an optional subprocess adapter with a declared working directory and environment allowlist. Tier 3 is an optional browser adapter. Tier 4 is an optional Docker/WSL/Windows Sandbox adapter. The core must never execute model-generated Python via `eval/exec`; it must never execute model-generated Python via eval/exec in the core or claim in-process isolation. If no hardened backend exists, execution returns `unavailable` or `simulation` with a full audit record.

Implement Gatekeeper-style side-effect handling: classify actions as read, write, network-read, external mutation, secret use or irreversible. For risky actions, prepare a simulated result and queue a reviewable approval; never pretend that a mutation completed. Capability grants are narrow, expiring and revocable. Secrets are injected only by an adapter and never placed in prompts, logs, memory or child envelopes.

### 3.7 Hermes-style learning loop with consent and evidence

Add bounded `USER_PROFILE`, `AGENT_MEMORY` and `SKILLS` projections, but keep the canonical store in the event-sourced memory system. A background reviewer may propose memory or skill changes after a run. It cannot directly apply them unless policy allows. Default mode is stage-for-review for new skills, policy changes, permissions, and facts with low evidence. Skill patches require diff, tests, security scan, provenance and rollback. Duplicate prevention and capacity limits are mandatory.

### 3.8 Safety and observability

Create a policy engine for prompt injection, exfiltration, path traversal, secret-like content, unsafe shell/network requests, unauthorized scope access, tool spoofing, and untrusted artifact instructions. Use deterministic rules first; optional model review is advisory and cannot override a deny. Add trace spans for planning, retrieval, tool calls, memory writes, approvals, resumes and failures. `inspect` must show why a fact or action was selected, which policy allowed it, and what was withheld.

## 4. Implementation order

### Phase A — Baseline and safety rails

Record clean working tree, current test/benchmark outputs, Python version, package version and current public API. Create a local backup tag or copy without publishing. Add an `IMPLEMENTATION_STATUS.md` and a change log. No core refactor before baseline is reproducible.

### Phase B — Schema, event integrity and capabilities

Add migrations, run/task envelopes, hash-chain audit, manifest validation, capability checks, secret redaction and quarantine behavior. Add unit tests for replay, corruption, duplicate command, stale lease, path escape and cross-tenant denial.

### Phase C — Durable sessions and context manager

Add message tree, forks, checkpoints, resumes, cancellation, compaction records and evidence-aware context packing. Add tests that crash at every checkpoint, recover exactly once, preserve source messages and respect token budgets.

### Phase D — Agent isolation and coordinator

Add AgentManifest, private/shared scopes, typed ResultEnvelope, broker/RPC, DAG planner, bounded parallelism and acceptance of memory proposals. Add leakage, deadlock, duplicate delivery and starvation tests.

### Phase E — Obsidian projection and evidence memory

Add Markdown vault projection/import, frontmatter schema, stable IDs, backlinks, conflict sets, freshness/decay, consolidation proposals and human review. Add recall benchmarks for exact facts, conflicting facts, temporal facts, entity relations and source attribution.

### Phase F — Gatekeepers and execution ladder

Add dry-run/simulation API, capability grant/revoke, side-effect classifier, subprocess adapter with explicit non-sandbox warning, and optional hardened backend interface. Do not activate arbitrary code execution by default. Add adversarial tests and a security decision log.

### Phase G — Hermes-style skill learning

Add staged skill proposals, diff/test/security gates, bounded memory capacity, duplicate prevention, reviewer budget and rollback. Demonstrate that a skill improves a held-out task without contaminating unrelated agents.

### Phase H — Evaluation, docs and release readiness

Add benchmarks and reports: recall precision/recall@k, evidence attribution, context retention after compaction, token/context reduction, resume success, agent isolation, policy deny rate, false-positive rate, secret non-leakage, tool latency and throughput. Update README, architecture, API, roadmap, security, examples and CHANGELOG. Keep GitHub publication disabled.

## 5. Quality gates

A phase may be marked complete only if all existing tests remain green, new tests cover its failure modes, public API compatibility is preserved or versioned, no secret enters logs or prompts, and a benchmark shows a real improvement against baseline. “More memory” is not accepted without better evidence-weighted recall or retention. “More agents” is not accepted without non-overlap and coordination metrics. “Safer” is not accepted without deny/allow adversarial tests and explicit limitations.

Minimum gates before local completion: 100% current tests pass; coverage remains at least the current project threshold; no cross-agent private-memory leakage in the adversarial suite; crash-resume correctness >= 99% in deterministic fault injection; evidence attribution >= 95% on the benchmark set; no secret/prompt-injection escape in the security corpus; context packer never exceeds configured budget; and every external mutation is staged or explicitly approved.

## 6. Two mandatory plan reviews before code changes

### Review 1 — architecture completeness

Check every requested capability against a concrete module, data structure, API, test and benchmark. Confirm that current stdlib-only constraints, Windows execution, local-only operation, backward compatibility, and no-GitHub-publish constraint are represented. Confirm that Cloudflare concepts are translated into local interfaces rather than copied blindly.

### Review 2 — threat model and anti-fake-improvement review

Attempt to break the plan with prompt injection, malicious Markdown, cross-agent retrieval, stale leases, replay tampering, path traversal, secret leakage, unsafe code execution, hallucinated memory, contradictory facts, context overflow, duplicate delegation and crash during write. Reject any phase that lacks a fail-closed behavior, an observable audit event, a test, and a rollback path.

Only after both reviews pass may implementation start. The first implementation action is Phase A baseline, not a broad rewrite.
