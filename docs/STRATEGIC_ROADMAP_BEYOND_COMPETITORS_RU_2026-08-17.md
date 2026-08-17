# Стратегический roadmap NOESIS: как превзойти конкурентов без фиктивных claims

## Executive position

NOESIS не должен пытаться победить OpenCode, Hermes или Cloudflare OS простым копированием количества tools. Сильная позиция — объединить их лучшие observable product patterns с более строгой моделью доверия: **zero-access startup, provenance-aware memory, taint-aware data egress, deterministic recovery, explicit human approval и доказуемая portability**.

Cloudflare OS задаёт эталон для workspace, typed capabilities, Gatekeepers и policy-following-data. OpenCode задаёт эталон для Plan/Build/subagent modes, scoped permissions и понятного UX разрешений. Hermes задаёт эталон для persistent memory, skills и gateway reach. NOESIS должен сделать эти элементы совместимыми в одном local-first control plane, сохранив private-by-default и stdlib core.

## Differentiation pillars

| Pillar | Target behavior | Why it can beat competitors | Proof required |
|---|---|---|---|
| Provenance memory | Каждое наблюдение, извлечение, summary, handoff и output получает resource lineage и sensitivity labels | Memory reuse не является фиктивным recall; policy follows what agent has seen | Leakage, recall, taint propagation and deletion tests |
| Zero-access capability OS | Agent starts with no network, files, tools or external resources; capability is typed, scoped, expiring and visible | Safer default than broad tool enablement | Deny-by-default holdout corpus and audit replay |
| Recovery-first agents | Best-state protection, immutable snapshots, patch review, rollback and resumable leases are first-class | Fewer catastrophic side effects and better long-running reliability | Kill/timeout/corruption recovery benchmark |
| Operator-grade Web UI | Cloudflare-style workspace graph, policy explanation, observation lineage, live approvals, provider health and isolation telemetry | User understands why an action is allowed/blocked instead of trusting a hidden agent | UI contract tests, screenshot review and red-team scenarios |
| Portable local gateway | DeepSeek/Hermes-compatible providers through one bounded contract; local process, Docker/Podman and native OS isolation are adapters | Avoids provider lock-in while keeping security policy centralized | Provider conformance and adapter security matrix |
| Safe executable skills | Skill manifests, provenance, digest, static preflight, capability declaration, child isolation and rollback | Skills become auditable packages rather than arbitrary plugins | Tamper, traversal, credential, network and downgrade tests |
| Honest evaluation | Same tasks, models, budgets and side-effect policy against Hermes/OpenCode and reference protocols | Prevents marketing claims and exposes real strengths/weaknesses | Reproducible benchmark artifacts and public methodology |

## Updated implementation sequence

### A. Security and data governance first

Implement an observation ledger, resource identifiers, sensitivity labels, provenance edges and taint propagation. Add egress policy that can deny an external request because the agent observed a restricted resource, even when the requested tool itself is normally allowed. Add policy simulation and explainability endpoints before enabling more tools.

Add a documentation linter that scans Markdown code fences and shell examples for credential-like strings, unsafe shell interpolation, `curl | sh`, unbounded `sudo`, destructive commands and claims that confuse simulation with execution. Every example should prefer argv arrays, file APIs, local loopback and explicit redaction.

### B. Cloudflare-style gateway and isolation

Define a `SandboxBackend` protocol with capability discovery, create/destroy, file operations, bounded process execution, network policy, resource quotas, logs and telemetry. Keep the current local child runtime as a clearly labelled bounded-process backend. Add optional Docker/Podman backend and native Windows/macOS adapters only when each backend passes an isolation conformance suite.

Define `Gateway` and `Gatekeeper` as separate layers. Gateway routes provider requests and sandbox operations. Gatekeeper owns credentials, resource scope, policy, approval, audit and observation lineage. No child process receives long-lived provider credentials; outbound handlers resolve credentials outside the child.

### C. Cloudflare-style Web UI

Replace the current simple session console with an operator console containing: workspace selector; agent topology; session timeline; provider health; capability inventory; policy explanation; observation/resource lineage; pending approvals; diff/patch review; child process status; CPU/memory/output budgets; network mode; and redacted audit export. Every potentially mutating action must show target, capability, data lineage, side effect, expiry and approval state before a commit button becomes available.

### D. Agent modes and execution

Add Plan, Explore, Build and Review modes. Plan and Explore are read-only by default. Build can prepare patches but cannot merge or publish without Gatekeeper commit. Review can inspect lineage, static findings, test results and rollback options but cannot edit. Multi-agent delegates receive non-overlapping claims and least-privilege workspaces.

### E. Evaluation and packaging

Run the fixed benchmark protocol in three lanes: contract-only, same-provider local execution and real terminal/tool workflows in disposable sandboxes. Report passed, failed, unsupported and not-run separately. Build Python 3.14 artifacts on native Windows and macOS separately using PyInstaller and Briefcase. Prefer PyInstaller onedir for debug evidence; package signed/notarized Briefcase or PyInstaller artifacts only after native smoke tests, SHA-256, SBOM/provenance and clean-room install tests.

## Security definition of done

A feature is not release-ready unless it has a typed contract, deny-by-default behavior, bounded inputs/outputs, redacted audit, negative tests, recovery tests, documentation-safe examples, provenance entry, license review and a clear statement of whether it is local verified, simulated, native verified or not run.

## Owner gates

The owner must provide or bind native Windows/macOS environments for native verification, choose whether Docker/Podman is an acceptable optional dependency, decide whether external provider credentials may be configured through user-owned connectors, and approve any release claim beyond private local release candidate status.
