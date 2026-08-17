# NOESIS runtime status and gap analysis — 2026-08-17

## Executive finding

NOESIS-Harness-Agent-Memory is currently a **stdlib-first durable memory and coordination kernel with a portable read-only control plane**. It is not yet a finished interactive agent application equivalent to Manus, Claude Code, OpenCode or Hermes Desktop. The repository intentionally implements the safety and state-management foundation before enabling model/tool execution.

## Why Python 3.14 is not the baseline

The package metadata declares `requires-python = ">=3.9"` and the CI matrix covers Python 3.9, 3.10, 3.11 and 3.12. The README identifies Python 3.11 as the currently verified laptop runtime. This is a compatibility policy, not a claim that Python 3.14 is undesirable.

Using Python 3.14 as the only portable baseline would narrow compatibility and would require a complete verification pass on Windows and macOS. The core deliberately uses stable standard-library APIs and SQLite WAL so that the same code can run on older supported Python versions. The correct approach is to add Python 3.14 as an **additional CI and compatibility target**, verify it on native Windows/macOS runners, and only then consider changing the minimum or recommended runtime. In the current sandbox, only Python 3.12 is installed and the 200-test suite passes there; Python 3.14 has not been verified.

A second distinction is important: the current portable launcher is portable in its install/data layout and process boundary, but it still requires a compatible Python runtime. It is not yet a self-contained single-file Windows `.exe` or macOS `.app` that bundles Python.

## What the current portable system actually does

| Component | Implemented behavior | Not implemented yet |
|---|---|---|
| `portable_launcher.py` | Separate install/data roots, `NOESIS_HOME`, platform-specific data placement, loopback control plane, startup probe and persistence sentinel | No model invocation, no skill entrypoint execution, no package installer, no Node/npm requirement |
| `health_server.py` | Read-only `GET /`, `/ui`, `/health`, `/models`; loopback default; optional authenticated LAN mode; bounded JSON; CSP and no-store headers | No POST command API, no session mutation, no model invocation endpoint |
| Embedded Web UI | Self-contained HTML showing health, models, capabilities and read-only sessions inventory; invocation button is disabled | No chat, streaming, tool approval, task editor, diff viewer, agent launch button or skill runner |
| `runtime_supervisor.py` | Starts an owner-supplied child `argv`, assigns random loopback port, probes `/health`, writes logs, performs bounded crash recovery and clean stop | Does not choose a model, interpret model output, generate commands or decide which agent/skill to run |
| `skill_import.py` + `skill_store.py` | Stages, scans, verifies digest, approves, installs immutable versions, updates active pointer transactionally and rolls back | Never imports Python modules or executes skill entrypoints; no UI-driven skill execution |
| Core memory/coordination | SQLite durability, evidence/provenance, bounded context, leases, recovery, best-state protection and cross-agent scope checks | No claim of OS-level sandbox or hardened remote execution |

The direct answer to “can we launch agents and skills now?” is therefore: **the supervisor can launch an explicitly supplied local child runtime, but the portable Web UI cannot yet launch an interactive model agent; the skill system can safely import/install/rollback skills but deliberately cannot execute their code.** This is an intentional security boundary, not an accidental missing button.

## Comparison with reference products

| Capability | NOESIS current state | OpenCode | Claude Code | Hermes Agent |
|---|---|---|---|---|
| Interactive coding agent | Not enabled in current Web UI | Terminal, desktop app and IDE extension; reads code, plans and makes changes [1] | Terminal, IDE, desktop and web surfaces; reads code, edits files and runs commands [2] | Interactive CLI/TUI and gateway [3] |
| Model/tool execution | Explicitly unavailable in coding adapter and UI | Core product capability [1] | Core product capability [2] | Core product capability [3] |
| Persistent memory | Strong experimental/verified kernel: provenance, bounded context, recovery and A/B evaluation | Product-specific context/configuration; not the same NOESIS memory model | Auto memory, `CLAUDE.md`, skills and hooks [2] | Curated persistent memory, session search and learning journey [4] |
| Skill execution/self-improvement | Safe manifest/import/store/rollback only; execution intentionally disabled | Custom commands/configuration [1] | Skills, hooks and custom agents [2] | Skills can be browsed/used and agent has a learning loop [3] [4] |
| Multi-agent coordination | Leases, dependency-aware claiming, non-overlap and recovery primitives | Agent modes and coding workflow [1] | Agent teams/background agents and Agent SDK [2] | Delegates and parallel subagents [3] |
| Desktop/Web UI | Read-only local control plane, not a product UI | Desktop/IDE/TUI surfaces [1] | Desktop/web/IDE/terminal surfaces [2] | CLI/TUI/gateway/desktop ecosystem [3] |
| Security posture | Conservative deny-by-default, AST-only verification, no claim of OS sandbox | Execution-oriented product with its own permissions and runtime model | Execution-oriented product with permissions, hooks and tool integrations | Execution-oriented product with tools, gateways and remote backends |

The comparison shows that NOESIS is not currently “the best in the world” as a complete agent product. It has a potentially distinctive foundation in **verifiable memory, explicit provenance, durable recovery, non-overlapping multi-agent ownership and conservative execution boundaries**, but it lacks the interactive execution surface and real-world benchmark evidence needed for a world-leading claim.

## Honest project status

The strongest accurate status is: **release-candidate core for a local-first, security-oriented agent OS foundation; portable read-only control plane verified; interactive agent runtime and executable skills are future gated components.** The repository has evidence for 200 passing tests, a clean release audit, zero actual AST `eval`/`exec` calls in core and a recall benchmark accuracy of 1.00 in its defined local benchmark. Those results do not establish superiority over products with different scopes, larger ecosystems, or production-scale evaluations.

## What must be built to approach the requested product level

The next product layer should be implemented behind explicit capability gates: a versioned task/session command API, a real interactive chat and streaming surface, per-agent workspaces, provider invocation adapters, approval-aware tool execution, diff/patch review, executable skills in a separate sandboxed child runtime, session resume, agent-team orchestration and native Windows/macOS packaging. Each feature needs focused security tests, failure recovery tests and cross-platform verification before it is called portable.

The safe architectural direction remains to keep the stdlib control plane as the source of truth and add execution as an isolated optional layer. A future Tauri shell may provide native packaging, but it would not by itself create the missing agent runtime or make the system secure. Python 3.14 should be added as a tested compatibility target rather than replacing the current `>=3.9` contract prematurely.

## References

[1]: https://opencode.ai/docs/ "OpenCode documentation"

[2]: https://code.claude.com/docs/en/overview "Claude Code overview"

[3]: https://github.com/NousResearch/hermes-agent "Hermes Agent repository"

[4]: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory "Hermes Agent persistent memory"
