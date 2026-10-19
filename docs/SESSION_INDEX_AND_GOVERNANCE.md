# Session indexing, retrieval and governance patterns (0.6 integration)

This document records the provenance and the ported designs of the 0.6
integration batch. Research snapshots of all upstream repositories live in
`../_research_2026-08/` (sibling of this repository). Nothing listed here is
vendored upstream source: every module is a clean-room reimplementation in
Python standard library, deterministic, and covered by unittest.

Provenance manifest: [third_party_provenance.json](third_party_provenance.json).
Notices: [../THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

## Summary

| Upstream | Language | Modules ported |
|---|---|---|
| deja-vu (`vshulcz/deja-vu`) | Go | 9 |
| harness-books (`wquguru/harness-books`) | Python/book | 5 |
| claude-code-book (`lintsinghua/claude-code-book`) | book | 4 |
| wshobson/agents (`wshobson/agents`) | Python | 6 |
| qm (`yc-software/qm`) | TypeScript | 6 |
| AI-Builder-Club/skills | Markdown/Python | 6 |
| **Total** | | **36** |

Earlier reference-only upstreams (LoopX, agentmemory, TencentDB, deepseek-harness,
Hermes, agent-teams, Cloudflare OS, OpenCode) are documented separately in
[../THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

## deja-vu (Go) - session history index

| Module | Ported design |
|---|---|
| `session_sources.py` | Data-driven harness/session-source adapter registry; discovery, cold parse and incremental parse are one declaration. |
| `inverted_index.py` | Prefix-sharded inverted index with delta-varint postings and BM25 scoring. |
| `retrieval_ladder.py` | Tiered retrieval ladder (exact, prefix, substring, fuzzy, relevance), freshness decay, UTF-8-safe byte-budget trim. |
| `untrusted_frame.py` | Untrusted-data framing and prompt-injection marker neutralization. |
| `source_refresh.py` | Manifest-as-cache with per-file state and prefix sampling; fresh/append/rewrite planning without reading whole files. |
| `sync_watermark.py` | Peer-scoped watermarked append-only sync; watermarks advance only after acknowledgement; dedupe ledger. |
| `atomic_write.py` | Atomic temp+rename writer with unique temp names and rename retry. |
| `tool_dialect.py` | Per-harness tool argument dialect as data, not code. |
| `parallel_parse.py` | Deterministic, fail-soft parallel fan-out parse with input-order results. |

## harness-books - harness engineering

| Module | Ported design |
|---|---|
| `authorization_gate.py` | Three-valued authorization gate (`allow`/`deny`/`ask`), sticky deny, no auto-escalation, risk tiers. |
| `ledger_closure.py` | Append-only causal ledger with mandatory closure; interrupted intents get a synthetic terminal record. |
| `circuit_breaker.py` | Circuit breaker on recovery itself plus a layered recovery ladder (cheapest fix first). |
| `instruction_layers.py` | Precedence-chain instruction layers and marked fragments; an append can never replace the base. |
| `fork_isolation.py` | Fork sub-contexts isolated by default, sharing only by explicit opt-in, cascade close on parent abort, one-way result channel. |

## claude-code-book - agent harness architecture

| Module | Ported design |
|---|---|
| `memory_index.py` | Typed file-based memory records and a bounded auto-loaded index (line and byte caps). |
| `extraction_queue.py` | Single-writer mutex plus a trailing extraction queue so no completed session is dropped. |
| `shared_board.py` | Shared persistent coordination board plus structured task notes. |
| `hook_engine.py` | Hook engine with a preview/run split and a stable display order. |

## wshobson/agents - multi-harness catalog

| Module | Ported design |
|---|---|
| `frontmatter.py` | Tolerant stdlib-only frontmatter parse and quote-safe emit. |
| `composite_score.py` | Layered weighted composite scoring with renormalization, anti-pattern penalty and confidence tiers. |
| `registry_reconcile.py` | Registry versus disk reconciliation with severity levels and remediation-carrying findings. |
| `projection_adapters.py` | Canonical source to per-consumer adapters; the source carries no consumer conditionals. |
| `namespace_registry.py` | Deterministic namespace and collision resolution for flat registries. |
| `elo_rank.py` | Deterministic Elo ranking with bootstrap confidence intervals and badges. |

## qm (TypeScript) - scoped multi-agent platform

| Module | Ported design |
|---|---|
| `scope_id.py` | Scope namespace (`kind:ref`) as the single isolation key, workspace layers and audience entitlement. |
| `blob_store.py` | Content-addressed SHA-256 blob store with atomic writes. |
| `acl_store.py` | Explicit owner-scoped ACL grants, no transitive re-share, membership-managed scopes. |
| `capability_token.py` | HMAC-SHA256 capability tokens bound to actor, scope, run and lease. |
| `leader_lease.py` | Durable leader lease (no double-firing), keyed queue and resilient sweeper. |
| `memory_revisions.py` | Append-only revision log, compare-and-swap replace, history/restore and cross-scope provenance. |

## AI-Builder-Club/skills - loop contracts

| Module | Ported design |
|---|---|
| `observation_log.py` | Two-layer append-only knowledge (current truth plus timeline) with frequency-counted dedupe. |
| `completion_sentinel.py` | File-sentinel completion protocol, idempotent READY marker and leased workspace id. |
| `loop_contract.py` | Loop domain contract: charter, cadence, artifacts and numeric gate conditions. |
| `verification_ledger.py` | Applied-change ledger with verify-after dates, capped fix loop and template-marker guard. |
| `metrics_collector.py` | Deterministic numeric metric collectors in JSONL, separate from agent-authored knowledge. |
| `loop_state.py` | Durable three-section loop state (Spec / Current understanding / Timeline). |

## Boundary

These modules keep the core contract: stdlib-only, deterministic, append-only
where state is durable, idempotent on every write path, and fail-closed where a
missing signal could otherwise be mistaken for success. They do not execute
model output, shell commands tools or skills; execution still crosses the
existing Trust Plane and ChildExecutionRuntime boundaries.
