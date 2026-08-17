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
