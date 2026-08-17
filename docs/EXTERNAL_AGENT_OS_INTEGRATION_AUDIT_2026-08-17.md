# External agent-OS integration audit — 2026-08-17

## Decision

NOESIS should **not** be rebuilt by copying Cloudflare OS, Hermes Agent or OpenCode wholesale. Their strongest ideas should be translated into explicit NOESIS contracts and optional adapters. The memory/security kernel must remain Python 3.14-only and stdlib-first; external runtimes must not become hidden mandatory dependencies.

## Source comparison

| Source | License/status observed | Valuable ideas | Why it cannot be the NOESIS core |
|---|---|---|---|
| Cloudflare OS | Apache-2.0; early-access repository | Agent chat UI, sandboxed gadgets, capability-based Gatekeepers, delayed human approval with simulation, private workspace instances and accountable agents | Built around TypeScript, Workers, Durable Objects, Dynamic Workers, Facets, Cap’n Web and `workerd`; cloud/runtime model is not a Python stdlib portable core [1] |
| Cloudflare Sandbox SDK | Apache-2.0; beta | Isolated containers, command execution, file operations, streaming, per-sandbox workspaces and service exposure | Requires Node.js, Docker/containers and Cloudflare deployment/runtime assumptions; useful as an optional remote sandbox adapter, not as local-first baseline [2] |
| Hermes Agent | MIT | Interactive CLI/TUI, gateway surfaces, persistent curated memory, session search, skills, learning loop, scheduling and parallel delegates | Broad runtime has Python/Node/native/tool dependencies and executes tools/skills; NOESIS must preserve stronger deny-by-default and provenance/rollback boundaries [3] |
| OpenCode | MIT | Terminal/desktop/IDE surfaces, plan vs build modes, undo/redo, model/provider configuration, subagents and coding workflow | OpenCode is a separate product/runtime with its own implementation and release surface; use its user-facing contracts as benchmark targets, not vendored implementation [4] |
| Claude Code | Proprietary product; not an integration source | Useful product benchmark: terminal/IDE/desktop/web, tools, skills/hooks, agents and sessions | Do not copy or vendor proprietary code; use only public behavior as an interoperability/benchmark reference [5] |

## Integration rules

The following are acceptable: implement compatible concepts independently; define NOESIS-native command/session/skill schemas; write optional provider and sandbox adapters; document inspirations and preserve license notices when code is actually reused; and use external products as black-box benchmark targets.

The following are not acceptable: copying source files without provenance review; importing Node/npm/Workers as hidden core dependencies; claiming that a subprocess is a hardened sandbox; granting skills unrestricted filesystem/network access; or treating simulated approval results as real side effects.

## Concrete translations into NOESIS

| External concept | NOESIS-native implementation target |
|---|---|
| Cloudflare Gatekeeper | `CapabilityGate` with typed tool request, scope, side-effect class, dry-run/simulation result, approval ticket, commit/reject decision and append-only audit |
| Cloudflare gadget | Per-agent workspace with manifest, owner, capability set, resource budget, snapshot lineage and destroy/recover lifecycle |
| Cloudflare delayed approval | Two-phase tool action: prepare/simulate first, then explicit commit; simulation must be marked as simulated and never enter factual memory as a completed side effect |
| Hermes memory/session search | Existing provenance-aware memory plus versioned session store, FTS/search index and separate durable session transcript; no silent memory overwrite |
| Hermes skills | `.noesisskill` manifest plus executable child runtime, immutable version, digest, capability allowlist, workspace mount policy, timeout, output limit and rollback |
| OpenCode plan/build/undo | Task/session API with `plan`, `approve`, `execute`, `review`, `commit`, `rollback`, `resume`; read-only plan mode and patch-based change review |
| OpenCode subagent | Multi-agent lease/claim model extended with isolated workspace, recipient scope, budget, parent task, evidence handoff and conflict-free merge |
| Desktop/web/TUI surfaces | One versioned session API with independent Python stdlib Web UI, terminal client and optional Tauri shell; no surface may bypass capability gates |

## Security boundary for child execution

The child runtime must be treated as a capability broker, not as a magic sandbox. Every invocation needs a signed/hashed request envelope, agent/tenant/session identity, executable or skill identity, explicit argv, environment allowlist, workspace root, read/write mounts, network policy, CPU/time/output budgets and approval state. The parent receives structured stdout/stderr/result envelopes and never trusts free-form output as a completed side effect.

The first implementation should support a local restricted profile and report limitations explicitly. Hardened OS isolation, container isolation or remote Cloudflare Sandbox execution must be separate adapters with their own verification. If no hardened adapter is available, dangerous tools remain `unavailable` rather than silently falling back to unrestricted execution.

## References

[1]: https://github.com/cloudflare/cloudflare-os "Cloudflare OS repository"

[2]: https://github.com/cloudflare/sandbox-sdk "Cloudflare Sandbox SDK"

[3]: https://github.com/NousResearch/hermes-agent "Hermes Agent repository"

[4]: https://github.com/anomalyco/opencode "OpenCode repository"

[5]: https://code.claude.com/docs/en/overview "Claude Code overview"
