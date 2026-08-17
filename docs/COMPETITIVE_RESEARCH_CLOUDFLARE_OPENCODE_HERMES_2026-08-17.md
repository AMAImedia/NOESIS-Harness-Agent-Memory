# Competitive research notes — 2026-08-17

## Cloudflare OS

Source: https://blog.cloudflare.com/cloudflare-os/

Cloudflare describes an agent workspace combining sessions, persistent state, outputs/files, resource access and an isolated runtime. The platform combines agent workspaces grounded in curated context/skills, a security/governance framework, and a platform for personal modifiable apps. It emphasizes that agents start with no access and request access to specific resources. Access is represented as typed capabilities; credentials remain outside generated code. Server code runs in a Dynamic Worker with global outbound networking disabled, while client code runs in a sandboxed browser frame and accesses the Internet only through explicit capabilities. Gatekeepers mediate service-specific resources/actions, hold credentials, enforce policy, record observed resources and control externally visible side effects. Cloudflare also describes policy following what the agent has seen, so sharing/hand-off/outbound requests can be restricted by data provenance.

## Cloudflare Sandbox SDK

Source: https://developers.cloudflare.com/sandbox/concepts/security/

The official security model states that each sandbox runs in its own VM, giving filesystem, process and network isolation plus resource limits. It warns that sessions sharing one sandbox can see the same files/processes and recommends separate sandbox IDs per user. It requires application-level authentication, input validation, rate limiting and application security. It recommends avoiding shell interpolation, using file APIs, keeping credentials outside the sandbox and using outbound handlers so the sandbox does not receive live credentials. Preview/tunnel URLs are bearer-like access paths and need application authentication. These findings imply that NOESIS must distinguish its current bounded process boundary from a real VM/OS sandbox and must not advertise equivalence without native isolation evidence.

## OpenCode

Sources: https://opencode.ai/docs/agents/ and https://opencode.ai/docs/tools/

OpenCode separates primary agents and subagents, including Build and Plan primary modes and General/Explore/Scout subagents. Plan is restricted by default: edits and bash require approval. Agent permissions can be allow/ask/deny and can be pattern-scoped for read, edit, bash, task, external directory, skill, webfetch and other tools. OpenCode supports max steps, model selection per agent, agent switching, subagent invocation, custom tools and MCP servers. The tool system includes bash, edit, write, read, grep, glob, apply_patch, skill, todo, webfetch and more. This is a strong product benchmark for agent modes, permission UX, scoped tools, plan/build separation and subagent navigation.

## Hermes

Search result and official repository references: https://github.com/NousResearch/hermes-agent and https://hermes-agent.nousresearch.com/docs/user-guide/features/skills

Hermes is relevant as a persistent-memory/skills/gateway reference. The current NOESIS audit treats Hermes as a black-box benchmark and architectural inspiration unless a specific source file and license obligation are audited. No external performance claim is made without running the fixed benchmark protocol.

## Strategic implications for NOESIS

The highest-value differentiation is not copying UI or adding unrestricted tools. NOESIS should combine Cloudflare-style observation-aware capabilities and credential isolation, OpenCode-style Plan/Build/Explore agent modes and scoped permissions, and Hermes-style persistent memory/skills/gateway reach with stronger provenance, rollback and secure-by-default policy. Required additions are: resource observation lineage, taint-aware outbound policy, typed capabilities with resource scope, separate sandbox adapter interface, policy simulation/explainability, secure documentation examples, structured prompt-injection holdouts, and reproducible external benchmark lanes.

## Native packaging findings

PyInstaller documentation states that the bundled interpreter and output are specific to the active operating system, Python version and architecture; a Windows or macOS artifact must be built on that OS under that Python version. One-folder mode is easier to debug than one-file mode. One-file mode extracts to a temporary directory and can leave temporary files after crashes; it must not be run with administrator privileges on Windows because of a shared-library tampering risk during preparation. macOS builds can target x86_64, arm64 or universal2 when the host Python supports it, and code signing options are platform-specific. Sources: https://pyinstaller.org/en/stable/operating-mode.html and https://pyinstaller.org/en/latest/usage.html.

Briefcase documentation states that macOS outputs include `.app` bundles or Xcode projects and can be packaged as DMG, ZIP or PKG; signing and notarization are part of the normal release path. It supports Python 3.10+ but native build and signing evidence remain platform-specific. Source: https://briefcase.beeware.org/en/stable/reference/platforms/macOS/.

Cloudflare Sandbox SDK is a TypeScript/Workers SDK and is not a drop-in Python local runtime. Its useful reusable concepts for NOESIS are per-user sandbox identity, VM/container isolation, resource quotas, streaming, file APIs, outbound handlers, application authentication and explicit cleanup. The repository is Apache-2.0, but its runtime requires its own Cloudflare/Docker/Node ecosystem. Source: https://github.com/cloudflare/sandbox-sdk.

## New strategic priorities

1. Add an observation ledger and taint labels to every resource read, output and handoff. Gatekeeper policy should follow data provenance, not only tool names.
2. Add Cloudflare-style zero-access startup: every agent starts with no resource, network or write capability; capabilities must be typed, scoped, expiring and visible in UI.
3. Add a provider-independent sandbox adapter interface with local bounded process, Docker/Podman, Windows Job Objects/AppContainer and macOS sandbox-exec/profile backends. Do not claim equivalent isolation across adapters.
4. Add Plan/Build/Explore/Review agent modes and pattern-based permissions, but make NOESIS default stricter: read-only until approval rather than OpenCode's documented default tool enablement.
5. Make the Web UI an operator console: workspace/agent graph, live policy explanation, observation lineage, pending approvals, patch review, provider health, process telemetry and exportable redacted audit.
6. Treat documentation as a security surface: examples must be copy-paste-safe, use argv/file APIs instead of shell interpolation, never include real-looking credentials, mark simulation versus execution, and run docs snippets through a static safety linter.
7. Run external A/B only in disposable, reproducible environments with identical task prompts, models, budgets and side-effect policy. Unsupported or unrun lanes must be reported as such.
8. Build PyInstaller and Briefcase artifacts separately on Windows and macOS Python 3.14 runners, prefer onedir for debugging and signed/notarized release artifacts, and publish SHA-256 plus SBOM/provenance records.
