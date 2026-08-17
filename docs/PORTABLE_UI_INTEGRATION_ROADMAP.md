# NOESIS Portable Control Plane

Date: 2026-08-17

## Decision

NOESIS should add a **portable, cross-platform control plane** for Windows and macOS, but it should not copy Hermes Studio, Hermes WebUI or DeepSeek Harness into the stdlib-only core. The correct design is a thin optional UI and runtime adapter around the existing NOESIS kernel.

The research found four useful implementation references. Hermes WebUI demonstrates a lightweight self-hosted browser interface with sessions, workspaces, profiles, providers, memory, skills, cron and authentication, and is MIT licensed [1]. DeepSeek Harness demonstrates a plugin/bundle architecture where model adapters, tools, sessions and the agent loop are replaceable [2] [3]. DSH Desktop demonstrates a desktop shell that launches a local child runtime, binds a random loopback port, persists profiles and plugins outside the installation directory, and validates portable preset packages [4] [5]. Hermes native Windows documentation demonstrates dependency provisioning, data persistence, scheduled startup and the remaining POSIX terminal limitation [6].

Hermes Studio is not a safe source for direct code reuse in NOESIS: its repository license is Business Source License 1.1, which grants non-commercial use but requires a separate commercial license for commercial use or embedding until the change date [7]. It remains a useful product-design reference only unless licensing is separately resolved.

## Candidate comparison

| Source | Reuse decision | What NOESIS should learn |
|---|---|---|
| Hermes WebUI | Reference and optional protocol client; no direct core dependency | Simple Python/vanilla UI, provider profiles, workspace/session panels, skill and memory surfaces, auth and health endpoints |
| DeepSeek Harness | Architectural reference; no runtime copy in core | Plugin seams, ordered profile/bundle composition, event-backed sessions, explicit capability providers and reversible overlays |
| DSH Desktop | Packaging and lifecycle reference | Child-runtime lifecycle, random loopback port, readiness checks, per-user data outside install directory, atomic preset import and platform-specific packaging |
| Hermes Studio | Product reference only until BSL/commercial terms are resolved | Information architecture for model/provider management, profiles, workflows, skills, memory, files and coding-agent surfaces |
| Hermes Open WebUI integration | Protocol reference | OpenAI-compatible local gateway can expose agent tools, memory and skills, but tools execute where the server runs; remote UI is not local execution [8] |

## Target architecture

The core remains `noesis_harness`, Python stdlib-only, local-first and independently usable without a browser. The new portable surface is an optional adapter with five layers:

| Layer | Responsibility | Dependency policy |
|---|---|---|
| NOESIS UI contract | Versioned local HTTP/JSON/SSE endpoints for health, profiles, models, sessions, tasks, memory, skills, approvals and audit | Python stdlib server; no provider secrets in browser payloads |
| Runtime supervisor | Starts and stops a local NOESIS worker, performs readiness checks, records logs, handles crash/restart and chooses a random loopback port | Separate process; no claim of hardened sandbox; report `unavailable` where hardening is absent |
| Provider adapter registry | OpenAI-compatible, Ollama, llama.cpp, vLLM, LM Studio, Hermes gateway and DeepSeek Harness endpoints | Config-only adapters; model names and endpoints are data, not hard-coded assumptions |
| Skill/package manager | Safe `.noesisskill` bundles with manifest, digest, path traversal/symlink rejection, stage/test/approve via existing `SkillGate` | No silent executable import; untrusted bundles require explicit approval |
| Desktop shell | Optional Electron or Tauri wrapper for Windows/macOS; browser mode remains first-class | Must be isolated from the core; platform artifacts are built and tested per architecture |

## Portable package contract

A portable distribution should have an installation directory containing only immutable runtime files and a separate user-data directory. On Windows, the default data root should be under `%LOCALAPPDATA%\\NOESIS`; on macOS, under `~/Library/Application Support/NOESIS`. An explicit `NOESIS_HOME` override must support a USB/SSD portable mode without embedding machine-specific paths.

The desktop shell should launch a child runtime with a generated random `127.0.0.1` port, wait for `/health`, open the UI only after readiness, and terminate the child cleanly on exit. It should never bind by default to `0.0.0.0`. If LAN access is explicitly enabled, the UI must require an auth token and show a security warning.

Every installation must store logs, SQLite state, skills, profiles, provider configuration and session data outside the installation directory. Updates must replace runtime files without deleting user data. Recovery must use the existing `BestStateStore`, `FiberStore` and `RecoveryCoordinator`; a failed child restart must return an explicit error and preserve the last verified state.

## Model and skill interoperability

The first release should accept any provider exposing a documented OpenAI-compatible endpoint or a local adapter implementing the NOESIS provider protocol. This covers local servers such as Ollama, llama.cpp, vLLM and LM Studio, as well as Hermes or DeepSeek Harness gateway endpoints. It must not imply that all models support the same tools, context length, vision, structured output or reasoning features. The UI should display capability metadata and fail-soft when a feature is unavailable.

NOESIS skills should use a format inspired by Hermes skills and DSH presets, but with an independent manifest and security policy. A bundle must contain a format version, identifier, declared capabilities, source digest, platform constraints and human-readable instructions. Import must stage into a temporary directory, reject absolute paths, parent traversal, backslash traversal and symlinks, run static security scanning, then pass through `SkillGate` for tests and explicit approval. Existing skill identifiers must never be silently overwritten. DSH `.dshpreset` archives should not be executed or copied directly; a future importer may translate only their declarative metadata after validation [5].

## Implementation roadmap

| Phase | Deliverable | Release evidence |
|---:|---|---|
| P0 | Versioned `NOESIS UI Contract v1` with `/health`, `/models`, `/profiles`, `/sessions`, `/tasks`, `/memory`, `/skills`, `/approvals` and `/audit` | Contract tests, schema fixtures, no-secret response scan |
| P1 | Stdlib local web server with vanilla UI shell and loopback auth | Windows/macOS smoke tests, random port, readiness and clean shutdown |
| P2 | Provider registry and model capability discovery | Ollama/llama.cpp/LM Studio/OpenAI-compatible fixtures, unavailable paths and redacted secrets |
| P3 | Safe `.noesisskill` package manager | Traversal/symlink/oversize tests, digest verification, SkillGate approval and rollback |
| P4 | Portable desktop wrapper | Windows x64 and macOS arm64 smoke artifacts; user-data migration and crash recovery |
| P5 | Hermes/DeepSeek bridge adapters | Local gateway fixtures, explicit tool-scope mapping, cross-agent leakage tests and audit events |
| P6 | Release-readiness | Full regression, fixed coding tasks, security corpus, clean secret scan, license inventory and owner approval |

## Non-goals and safety boundaries

The first portable release will not claim to be a hardened sandbox, will not execute model-generated Python in-process, will not silently install arbitrary plugins, will not expose provider tokens to the browser, and will not merge Hermes/DSH private memory merely because two profiles are visible in the same UI. Cross-agent sharing remains explicit, scope-checked and audit-backed.

The desktop wrapper is a distribution surface, not a security boundary. If a user requires OS-level confinement, NOESIS must integrate an independently verified sandbox provider and report `unavailable` when it is not present.

## Next implementation gate

The next code phase should implement P0: a small versioned stdlib UI contract and `/health`/`/models` read-only adapter, followed by contract tests. It should not begin with Electron or a full dashboard. This keeps the core portable, makes provider compatibility measurable, and prevents the UI from becoming a second untested agent runtime.

## References

1. [Hermes WebUI](https://github.com/nesquena/hermes-webui) — MIT web interface, profiles, providers, memory, skills and Windows/WSL notes.
2. [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) — official DeepSeek plugin-oriented harness.
3. [DeepSeek Harness architecture](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md) — profiles, bundles, plugin seams and event-backed sessions.
4. [DSH Desktop](https://github.com/dataelement/dsh-desktop) — MIT desktop wrapper, lifecycle, loopback and cross-platform packaging.
5. [DSH preset package contract](https://github.com/dataelement/dsh-desktop/blob/main/docs/preset-packages.md) — validation, atomic install and trust warnings.
6. [Hermes native Windows guide](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/windows-native.md) — native Windows support and dependency matrix.
7. [Hermes Studio LICENSE](https://raw.githubusercontent.com/EKKOLearnAI/hermes-studio/main/LICENSE) — Business Source License 1.1 and commercial-use restriction.
8. [Hermes Open WebUI integration](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/open-webui) — OpenAI-compatible gateway and server-side tool execution boundary.
