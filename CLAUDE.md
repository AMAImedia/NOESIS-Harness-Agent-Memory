# CLAUDE.md — NOESIS-Harness-Agent-Memory (agent context)

Local-first, **stdlib-only** agent-memory harness with strict honesty gates and
fail-closed evidence. Deterministic core (storage/recall/coordination) never
calls an LLM; the LLM is optional and only ever a pluggable callback.

## Hard rules (full text in AGENTS.md)
1. Zero dependencies in `noesis_harness/` — stdlib only.
2. Deterministic core; LLM optional (pluggable callbacks only).
3. Append-only state — never mutate the event log; replay to project.
4. Idempotent writes (event_id fingerprints, content dedup, TTL leases).
5. Never delete files — move to `_archive/<name>_<date>/`.
6. Tests with every change: `python -m unittest discover -s tests -q` must stay
   green; also run `python benchmarks/recall20.py`.

## Current state (2026-08-27)
- Local gates 1-8 executed; full suite ~1160 tests OK, recall20 20/20 acc=1.00.
- Native Windows exe self-signed (dev cert) — NOT a release claim; no CA cert,
  no macOS host.
- External lanes (Hermes/OpenCode/DeepSeek Harness): OpenCode model_task passed
  via proxy-jail; Hermes/DeepSeek blocked (no credentials / no profile).
- Autoloop runs (`scripts/noesis_autoloop_keeper.cmd` + `scripts/noesis_autoloop.py`,
  PID ~5032) every 600s; green cycle 385+.
- Addon: `addons/t_search_bridge.py` — optional t-search-harness lens over NOESIS
  memory, disabled by default, fails closed.

## Key commands
- Suite: `py -3.14 -m unittest discover -s tests -q`
- Links: `py -3.14 scripts/check_markdown_links.py --root .`
- Docs security: `py -3.14 scripts/docs_security_audit.py --root .`
- Release audit: `py -3.14 scripts/release_audit.py --root .`
- Bench: `py -3.14 benchmarks/recall20.py` and `benchmarks/workload20.py`
- TEMP must be repo `_temp`: `$env:TEMP = "<repo>\_temp"`.

## Key files
- `noesis_harness/event_store.py` — append-only JSONL log + projection.
- `noesis_harness/proxy_jail.py`, `appcontainer_backend.py` — model_task gating.
- `scripts/pinned_runner_adapter.py`, `external_runner_contract.py` — external lanes.
- `docs/` — curated working docs only (see `docs/README.md`); per-wave memos in
  `_archive/`.
- `addons/t_search_bridge.py` — optional retrieval lens.

## Honesty boundary (non-negotiable)
- `not_run` / `blocked` = missing host/credentials, never a disguised failure.
- No native-parity, no competitor-superiority, no "world-leading" claims without
  matching evidence.
- Secrets/keys never logged or committed.
