# NOESIS-Harness-Agent-Memory

Local-first, zero-dependency (stdlib-only) agent-memory harness with strict
honesty gates and fail-closed evidence policy, verified on Python 3.14. Storage,
recall and coordination never call an LLM; the LLM is optional and only ever a
pluggable callback.

## Quick start
- Read the rules first: [AGENTS.md](AGENTS.md).
- Run the suite: `python -m unittest discover -s tests -q` (expect ~1160 tests, OK).
- Benchmarks: `python benchmarks/recall20.py` (target acc=1.00).
- Documentation index: [docs/README.md](docs/README.md).

## What is real (honesty boundary)
- Local gates 1-8 are executed and recorded with machine-readable evidence.
- External agent-OS lanes (Hermes / OpenCode / DeepSeek Harness) are pinned and
  verified only when an operator supplies matching hosts and credentials. Without
  them they report `not_run` / `blocked` — never a fabricated pass.
- Native Windows/macOS artifacts require a target host and a CA code-signing
  certificate; a self-signed dev-signed Windows exe exists but is NOT a release
  claim. No macOS host is available here.
- No superiority or native-parity claims are made without matching evidence.

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

The repository is a private GitHub repository; publication remains owner-approved gates.
