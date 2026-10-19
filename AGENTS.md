# AGENTS.md — NOESIS Harness Agent Memory

Instructions for AI coding agents working in this repo.

## Rules (hard)

1. **Zero dependencies** — the `noesis_harness/` package must stay stdlib-only
   (`sqlite3`, `hashlib`, `json`, `threading`, `time`, `uuid`, `os`, `math`).
   No numpy, no requests, no pandas. This is the whole point: local-first, no
   install friction.
2. **Deterministic core, LLM optional** — storage/recall/coordination never call
   an LLM. If you add compression, it must be a pluggable callback, not a hard
   dependency.
3. **Append-only state** — never mutate the event log. State is always a replay
   projection. If you need a new fact, append an event, don't edit an old one.
4. **Idempotency on every write path** — `event_id` fingerprints, content dedup,
   TTL leases. A double-send must be a no-op, not a duplicate.
5. **Never delete files** — move to `_archive/<name>_<date>` instead.
6. **Tests with every change** — `python -m unittest discover -s tests -q` must
   stay green (67+). Also `python benchmarks/recall20.py`. No external test deps.

## Style

- Python 3.9+ compatible (no `X | None` syntax in signatures, no `match`).
- English only in code/comments. No emoji.
- Each module starts with a docstring naming the systems it borrows patterns
  from (provenance matters for this project).
- Typed statuses as string enums, not scattered booleans.

## Provenance discipline

Every non-trivial module documents its source patterns (LoopX, agentmemory,
TencentDB, deepseek-harness, Hermes, agent-teams). When you port a new pattern,
add the source to the module docstring and to `../RESEARCH_DAIGEST.md`.

## Owner communication (recorded 2026-09-18)

- The repository owner is not a programmer (student). Explain every change in
  plain language, no jargon, with a simple "what changed and why".
- Chat replies to the owner MUST be in Russian. Code, docstrings, comments,
  commit messages, and repository documentation stay English.
- Before starting a non-trivial task, restate your understanding and ask for
  confirmation first.
- End every work batch with an honest "before -> after" report in simple terms.

## Integration sources (repos read, patterns ported)

- deja-vu (Go), harness-books, claude-code-book, wshobson/agents, qm (TypeScript),
  AI-Builder-Club/skills. Research copies live in `../_research_2026-08/`.
  Ported modules are clean-room reimplementations, never vendored code.
  See `docs/SESSION_INDEX_AND_GOVERNANCE.md` and `docs/third_party_provenance.json`.
