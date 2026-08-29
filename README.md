# NOESIS-Harness-Agent-Memory

Local-first, zero-dependency (stdlib-only) agent-memory harness with strict
honesty gates and fail-closed evidence policy, verified on Python 3.14. Storage,
recall and coordination never call an LLM; the LLM is optional and only ever a
pluggable callback.

## Quick start
- Read the rules first: [AGENTS.md](AGENTS.md).
- Run the suite: `py -3.14 -m unittest discover -s tests -q` (expect ~1397 tests, OK).
- Benchmarks: `py -3.14 benchmarks/recall20.py` (target acc=1.00).
- Native exe: `dist/noesis-harness.exe` (self-signed dev cert).
- Documentation index: [docs/README.md](docs/README.md).

## What is real (honesty boundary)
- **Local gates 1–5, 9**: executed, passed, evidence byte-stable (recall20 20/20, quality score 0.979, recall gain 1.0).
- **Gate 6** (native): Windows exe built (dev-signed, 11MB); macOS not_run (no host).
- **Gate 7** (external A/B): not_run — users supply API keys at runtime (like OpenCode).
- **Gate 8** (release): pending human review.
- **Stage 10**: requires named reviewer.
- No superiority or native-parity claims are made without matching evidence.
- `NOESIS_VECTOR_BACKEND=none` pinned for deterministic evidence across hosts.

## Evidence (current, byte-stable)
| Metric | Value |
|--------|-------|
| Local tests | 1397 OK (18 skipped) |
| recall20 | 20/20 acc=1.00 |
| Memory quality (v3) | quality_score 0.944, recall 1.0 |
| Multi-session quality | quality_score 0.979, recall 0.833 |
| Recall gain (baseline→nextgen) | 1.0 |
| Synthetic fixture (security_holdouts) | by-design, not a leak |

## Security boundary
The deterministic core is stdlib-only and does not execute model-generated
Python in-process. It provides capability decisions, auditability, logical
private scopes and fail-soft execution status. It does NOT replace an OS sandbox,
VM, container or hardened remote execution service; the execution ladder returns
`unavailable` when such an adapter is not configured.

## Provenance
Design references Cloudflare OS / Project Think (capability access, durable
execution, sub-agent isolation), LoopX, agentmemory, TencentDB, deepseek-harness,
Hermes and agent-teams as patterns — local Python/SQLite interpretations, not
copies or dependencies. License/attribution: the project is distributed under the MIT License; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and
[third_party_provenance.json](docs/third_party_provenance.json).
Security policy: [SECURITY.md](SECURITY.md).

## How to make public
1. Go to `https://github.com/AMAImedia/NOESIS-Harness-Agent-Memory/settings`
2. Scroll to "Danger Zone" → "Change visibility"
3. Select "Public" → confirm
4. Or via CLI: `gh repo edit AMAImedia/NOESIS-Harness-Agent-Memory --visibility public`

**Required before publishing**: ensure README boundaries are understood by users — no superiority claims, honest `not_run`/`blocked` status for external lanes.
