# Install for Agents

Instructions for AI coding agents (Claude Code, Codex, OpenClaw, Cursor,
Copilot, etc.) working in this repo.

## TL;DR

- **Zero dependencies.** Do not `pip install` anything into this repo.
- **Tests:** `python -m unittest discover -s tests -v` (stdlib only).
- **Core files:** `noesis_harness/{event_store,memory,coordination}.py` -
  read `AGENTS.md` before touching them.
- **Never delete files.** Archive to `_archive/<name>_<date>` instead.
- **English only** in code and comments. No emoji. Python 3.9+ syntax.

## Your job by area

| Area | What agents do |
|------|----------------|
| `noesis_harness/` | **Read-only unless assigned the core task.** Idempotency and append-only rules apply. |
| `tests/` | Add tests for new behavior. Run the whole suite after every change. |
| `examples/` | New self-contained runnable demos. One file = one scenario. |
| `integrations/` | Local adapters (STUB or WIRED - mark in the docstring). Never a real network client. |
| `benchmarks/` | Measure ops/sec + disk size. Print a table. |
| `docs/` | Architecture, API, why, recipes. Keep English, concise, pattern-sourced. |

## Verification checklist before finishing

1. `python -m unittest discover -s tests -v` - all green.
2. Your example/integration/benchmark runs without errors.
3. `python -m build` still works (if you touched packaging).
4. No files deleted; anything superseded moved to `_archive/`.
5. `CHANGELOG.md` updated under `[Unreleased]`.

## Common traps

- **FTS5 syntax** - `[`, `]`, `:` are special in FTS5 MATCH. Escape or use
  substring fallback for identifiers like `[codex:sid]`.
- **Windows console encoding** - emoji and non-ASCII in `print()` crash on
  cp1252. Use ASCII in stdout, or encode with `errors="replace"`.
- **sqlite3 lock** - hold `self._lock` around write transactions; use
  `PRAGMA journal_mode=WAL` + `busy_timeout`.
- **Self-deadlock** - never call a locked method (`remember()`) while holding
  the same `threading.Lock` in a method like `consolidate_session()`.
- **`__main__` vs module name** - `python -m foo` runs the file as `__main__`;
  monkey-patching `import foo` does NOT patch `__main__`. Patch
  `sys.modules['__main__']` too, or test the class directly.

## Verification loop for coding agents

Run from the repo root after every change:

1. `python -m unittest discover -s tests -v` - all green.
2. `python benchmarks/recall20.py` - fixed 20-query recall gate, exit 0 expected.
3. `python benchmarks/workload20.py` - fixed work-product gate, exit 0 expected.
4. `python scripts/check_markdown_links.py --root .` - documentation link audit clean.
