# NOESIS-Harness-Agent-Memory

[![License: MIT](https://img.shields.io/badge/license-MIT-76B900.svg)](LICENSE)
[![Platform: Windows%20%7C%20Linux%20%7C%20macOS](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-111827.svg)](#portability)
[![Python: 3.14](https://img.shields.io/badge/python-3.14-76B900.svg)](#requirements-and-runtime)
[![Core: stdlib-only](https://img.shields.io/badge/core-stdlib--only-111827.svg)](#requirements-and-runtime)

> **A local-first durable memory and coordination kernel for multi-agent systems.**
>
> Persistent state, evidence-weighted recall, bounded context, explicit capabilities and non-overlapping work ownership without mandatory runtime dependencies.

NOESIS-Harness-Agent-Memory is a portable Python library for building local agent runtimes that can persist state, recover work after interruption, coordinate multiple agents and expose security decisions explicitly. It is designed for researchers and developers who need a deterministic, inspectable foundation rather than an ambient-permission agent loop.

The core package is **stdlib-only**. LLM providers, external services and hardened sandboxes are optional adapters; the deterministic storage, memory, coordination and governance layers do not call an LLM.

## At a glance

| Item | Details |
|---|---|
| Primary task | Durable memory, context assembly, multi-agent coordination and policy-aware execution planning |
| Input | Structured events, messages, tasks, evidence records and capability requests |
| Output | SQLite-backed state, source-attributed context, audit records, result envelopes and typed status decisions |
| Interface | Python library, examples and benchmark scripts; no web UI is required |
| Pipeline/backend | Python standard library with SQLite WAL; optional integrations are kept outside the core |
| Default state | Local-first, deny-by-default capabilities, explicit provenance and fail-soft status reporting |
| Server | None required; the core is an in-process library and does not claim process isolation |
| License | MIT |

## Why use it

NOESIS keeps the agent kernel small and inspectable: register durable work, persist checkpoints, store evidence with provenance, assemble context under a hard budget, coordinate leases and review side effects through explicit gates. Once the local Python runtime is available, the test suite and benchmarks run without downloading a framework or connecting to a hosted control plane.

This repository is a clean-room, local-first implementation informed by publicly documented capability and durability patterns from [Cloudflare OS](https://github.com/cloudflare/cloudflare-os), [Project Think](https://blog.cloudflare.com/project-think/), [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness), [OpenClaw](https://github.com/openclaw/openclaw), [Hermes Agent](https://github.com/NousResearch/hermes-agent) and other documented agent systems. These are architectural and benchmark references, not copied source, endorsement, affiliation or runtime dependencies. NOESIS translates selected principles into a local, stdlib-only Python design and keeps the limitations visible.

## Highlights

- **Durable execution primitives:** SQLite-backed fibers, monotonic checkpoints and recovery after fault injection.
- **Evidence-weighted memory:** provenance and source IDs, confidence, freshness decay, duplicate merging and review-only conflict proposals.
- **Bounded long context:** priority-aware assembly with a hard token cap, required blocks, dropped-item audit and source provenance.
- **Non-overlapping coordination:** dependency-aware task claiming, single-live-owner leases, TTL reclaim and duplicate-completion suppression.
- **Capability governance:** deny-by-default manifests, gatekeeper decisions, pending simulation, approval boundaries and an explicit execution ladder.
- **Auditable isolation model:** private scopes and cross-tenant denial at the broker layer, with no claim that this replaces OS-level or process-level isolation.
- **Deterministic security checks:** prompt-injection patterns, token-like secrets, invisible Unicode, unsafe `eval`/`exec` use and path traversal checks, plus a local execution contract with network disabled by default.

## Quick start

1. Install Python 3.14. Python 3.14 is the sole target runtime for the next NOESIS agent-OS generation; native Windows/macOS verification remains a release gate until runners are available.
2. Clone or copy the complete repository and open a terminal in its root directory.
3. Run the full regression suite:

   ```text
   python -m unittest discover -s tests -v
   ```

4. Run the next-generation benchmark:

   ```text
   python benchmarks/nextgen_bench.py --n 100
   ```

5. Run the coordination and context-engine task benchmark:

   ```text
   python benchmarks/coordination_context_bench.py --n 100
   ```

No system-wide installation is required for the core tests. An isolated virtual environment is recommended for optional adapters. The repository now contains a stdlib read-only control-plane Web UI at `/` and `/ui`; it is not yet the full interactive agent surface. Model invocation, session mutation and executable skill entrypoints remain gated future layers.

## How the workflow works

The harness separates durable state, memory selection, coordination and execution policy instead of treating them as one unrestricted agent loop.

| Stage | What happens |
|---|---|
| 1. Declare capabilities | An agent run receives an explicit manifest. Capabilities are denied by default and are auditable. |
| 2. Persist execution | Commands, fibers and checkpoints are stored durably in SQLite. Recovery resumes only from monotonic persisted state. |
| 3. Curate memory | Evidence records keep provenance, confidence, freshness and conflicts. Context assembly obeys a hard budget and records what was dropped. |
| 4. Coordinate and govern | Agents claim dependency-ready work under leases. Gatekeepers, scope checks and execution status decisions prevent ambient side effects. |
| 5. Review results | Result envelopes, audit chains and projection helpers make outcomes inspectable before they are consolidated or externally applied. |

## Requirements and runtime

The deterministic core intentionally has no mandatory third-party runtime dependency. It uses Python’s standard library and SQLite, including WAL mode and explicit connection cleanup for Windows compatibility. Optional LLM or service integrations must remain outside the core contract.

| Requirement | Verified project value |
|---|---|
| Operating system | Windows workflow verified; the core uses portable Python and SQLite APIs |
| Hardware | CPU is sufficient for the core; model inference requires separate local or remote infrastructure |
| Runtime | Python `3.14` only; native Windows/macOS verification pending |
| Local assets | No model is required for deterministic tests, memory, coordination or governance benchmarks |
| Disk space | Small for the core; generated SQLite state, logs, model files and optional adapters are user-managed |

## Portability

Run commands from the repository root so that package imports, examples and benchmark paths resolve consistently. SQLite connections are managed explicitly and temporary database files are excluded from public commits. The core does not require a daemon, cloud account or fixed port; the portable launcher exposes a local read-only Web UI, while the interactive agent runtime is being built as an isolated next layer.

The execution ladder reports `unavailable` when a hardened sandbox is not configured. This is deliberate: the project does not present an in-process guard as a secure OS-level sandbox. The core also does not execute model-generated Python through `eval` or `exec`.

Heavy models, downloaded binaries, runtime environments, generated output, local databases, logs, caches and private integration credentials must remain outside the Git repository. The portable `.exe`/`.app` bundling pipeline is a future Python 3.14 release gate. Use `.env.example` only as a variable-name reference; never commit a populated `.env` file.

## Privacy and security

The default design is local-first. Data written by the core remains in caller-selected local SQLite or filesystem locations unless an optional integration explicitly exports it. Capability manifests, private scopes, audit chains and local execution contracts make security decisions visible, but they do not grant a false promise of perfect containment.

Do not publish private prompts, media, source files, generated output, browser profiles, cookies, tokens, API keys, local paths, databases, logs or downloaded model payloads. Never place credentials in README files, issues or commits. Review every optional integration before enabling network access or side effects.

The isolation broker provides logical private scopes and cross-tenant denial. It is not a replacement for operating-system permissions, a VM, a container, a Windows Sandbox or a hardened remote execution service.

## Troubleshooting

| Symptom | What to check |
|---|---|
| `ModuleNotFoundError` while running a test or benchmark | Run the command from the repository root and use the documented `python -m unittest` command. |
| SQLite file remains locked on Windows | Stop the process that owns the database and use the repository’s managed connection patterns; generated database files are disposable. |
| A task cannot be claimed | Check dependency completion and lease TTL; the coordinator only exposes dependency-ready work and permits one live owner. |
| Context output is shorter than the input | Inspect the dropped-item audit. The assembler enforces the hard token budget rather than silently exceeding it. |
| Sandbox execution reports `unavailable` | Configure a reviewed hardened adapter; do not treat the local fallback as a security sandbox. |
| Benchmark results differ | Record Python version, OS, `--n` value and database location. Local measurements are not universal performance claims. |

For technical details, see [`docs/README.md`](docs/README.md), [`docs/ARCHITECTURE_1.0_NEXTGEN.md`](docs/ARCHITECTURE_1.0_NEXTGEN.md) and [`docs/EVALUATION_PROTOCOL.md`](docs/EVALUATION_PROTOCOL.md).

## File map

| Location | Purpose |
|---|---|
| `noesis_harness/` | Stdlib-only deterministic kernel and public primitives. |
| `tests/` | Unit and integration tests for memory, durability, coordination, governance and security. |
| `benchmarks/` | Reproducible local benchmark scripts and benchmark input data. |
| `examples/` | Small usage examples for the legacy and next-generation layers. |
| `integrations/` | Optional provider or agent-loop adapters; not required by the core. |
| `docs/` | Architecture, plans, evaluation protocol, API notes and implementation reports. |
| `.env.example` | Names of optional environment variables; contains no credentials. |
| `.gitignore` | Local protection rules for secrets, databases, logs, caches, archives and build artifacts. |

## License and third-party components

NOESIS-Harness-Agent-Memory is licensed under the [MIT License](LICENSE). Third-party reference and provenance boundaries are recorded in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [`docs/third_party_provenance.json`](docs/third_party_provenance.json).

The project is informed by publicly available design discussions and open-source projects, including Cloudflare OS and Project Think, DeepSeek Harness plugin composition, OpenClaw gateway and cross-platform UX, Hermes Agent memory/skills/gateway practices, Pi’s minimal harness and Letta’s memory-tier concepts. These references are design inputs, not bundled runtime dependencies. Their names, source code and licenses remain governed by their respective repositories. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), the [evaluation protocol](docs/EVALUATION_PROTOCOL.md) and [architecture notes](docs/ARCHITECTURE_1.0_NEXTGEN.md) for the boundary between inspiration and implemented behavior.

## References

1. [Cloudflare OS repository](https://github.com/cloudflare/cloudflare-os) — capability-based Gatekeepers, private gadgets, agent accountability and sandbox-oriented architecture.
2. [Project Think: building the next generation of AI agents on Cloudflare](https://blog.cloudflare.com/project-think/) — durable execution, fibers, sub-agents, session trees and the execution ladder.
3. [NOESIS architecture 1.0](docs/ARCHITECTURE_1.0_NEXTGEN.md) — local implementation boundaries and design decisions.
4. [NOESIS evaluation protocol](docs/EVALUATION_PROTOCOL.md) — benchmark criteria and release gates.
5. [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) — plugin-oriented harness reference and benchmark target.
6. [OpenClaw](https://github.com/openclaw/openclaw) — personal-agent gateway, skills/plugins and cross-platform surface reference.
7. [Hermes Agent](https://github.com/NousResearch/hermes-agent) — persistent memory, skills, gateway and delegate reference.

---

## Publication checklist

Before any public push, confirm that all placeholders are absent; `LICENSE` and the README license badge agree; every relative link resolves; `.env`, databases, logs, caches, archives and model payloads are ignored; secret-pattern scans are clean; the test suite passes on the intended Python versions; and the owner has explicitly approved the remote repository, branch and first push.

This repository is maintained in a **private GitHub repository** for now. Public visibility, first public release and any irreversible publication remain owner-approved gates; private remote presence does not imply a public release.
