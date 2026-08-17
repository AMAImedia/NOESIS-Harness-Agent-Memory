# Contributing to NOESIS-Harness-Agent-Memory

Thanks for helping make this the best local-first agent framework.

## Ground rules (hard)

1. **Zero dependencies in the core.** `noesis_harness/` is stdlib-only
   (`sqlite3`, `hashlib`, `json`, `threading`, `time`, `uuid`, `os`, `math`).
   No numpy, no requests, no pandas, no third-party packages. Ever.
2. **Deterministic core, LLM optional.** Storage/recall/coordination never
   call an LLM. Compression is a pluggable callback.
3. **Append-only state.** Never mutate the event log. Add a fact by appending
   an event, not by editing history.
4. **Idempotency on every write path.** event_id fingerprints, content dedup,
   TTL leases. A double-send must be a no-op.
5. **Never delete files.** Move to `_archive/<name>_<date>` instead.
6. **Tests with every change.** `python -m unittest discover -s tests -v`
   must stay green. No external test deps.
7. **Python 3.9+ compatible.** No `X | None` in signatures, no `match`.
8. **English only** in code, comments, and docs. No emoji in code.
9. **Provenance discipline.** Every module docstring names the systems it
   borrows patterns from (LoopX, agentmemory, TencentDB, deepseek-harness,
   Hermes, agent-teams).

## How to contribute

1. Fork the repo and create a branch: `git checkout -b feature/your-change`.
2. Make the change. Keep it small and focused (one file = one job).
3. Add or update tests in `tests/`.
4. Run the suite:
   ```bash
   python -m unittest discover -s tests -v
   ```
5. Run examples and benchmarks to confirm nothing regressed:
   ```bash
   python examples/botfarm_lead.py
   python benchmarks/run_bench.py --all
   ```
6. Update `CHANGELOG.md` under `[Unreleased]`.
7. Open a pull request describing the change and the pattern source.

## File ownership

| Path | Owner |
|------|-------|
| `noesis_harness/` | core maintainers only |
| `tests/` | core maintainers only |
| `examples/`, `integrations/`, `benchmarks/`, `docs/` | one file = one contributor per PR |

Do not edit files outside your change's scope in the same PR.

## Commit style

- Imperative mood: "Add memory decay", "Fix lease renewal race".
- Reference the pattern source when porting: `(pattern: agentmemory leases.ts)`.
- One logical change per commit.

## Questions

Open an issue. We answer fast.
