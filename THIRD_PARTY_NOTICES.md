# Third-party notices and integration provenance

NOESIS-Harness-Agent-Memory is not a copy of any upstream agent product. The current private core contains no vendored source from the projects below; they are recorded as architectural references and future optional integration sources. Names in this file identify provenance and benchmark references, not endorsement, affiliation or copied implementation.

## Cloudflare OS

- Source: https://github.com/cloudflare/cloudflare-os
- License: Apache License 2.0
- Planned use: capability Gatekeeper concepts, delayed approval/simulation model, private workspace/gadget isolation patterns.
- Current code reuse: none.
- Redistribution obligations if code is reused: include Apache-2.0 license, preserve copyright/patent/trademark/attribution notices, mark modified files, include applicable NOTICE content, and retain provenance.
- Trademark: Cloudflare names and marks are not granted by the Apache-2.0 license.

## Cloudflare Sandbox SDK

- Source: https://github.com/cloudflare/sandbox-sdk
- Package license: Apache License 2.0 at `packages/sandbox/LICENSE`.
- Planned use: optional remote/container sandbox adapter and reference for workspace/streaming execution APIs.
- Current code reuse: none.
- Architectural limitation: it requires Node.js and Docker/Cloudflare runtime assumptions; it is not part of the Python 3.14 stdlib core.

## Hermes Agent

- Source: https://github.com/NousResearch/hermes-agent
- License: MIT License.
- Planned use: benchmark target and optional interoperability ideas for session search, skills, gateway surfaces and multi-agent delegates.
- Current code reuse: none.
- Redistribution obligations if code is reused: retain the copyright and MIT permission notice in copies or substantial portions; audit all separately licensed dependencies, assets and bundled skills.

## OpenCode

- Source: https://github.com/anomalyco/opencode
- License: MIT License.
- Planned use: benchmark target and independent implementation reference for plan/build modes, diff review, undo/redo, terminal/desktop surfaces and subagents.
- Current code reuse: none.
- Redistribution obligations if code is reused: retain the copyright and MIT permission notice; inspect dependencies and upstream notices.

## DeepSeek Harness

- Source: https://github.com/deepseek-ai/deepseek-harness
- License: verify against the upstream repository license and release notices before any code reuse.
- Planned use: reference and benchmark for plugin-oriented model/tool/skill/session/sandbox composition.
- Current code reuse: none.
- Redistribution obligations if code is reused: audit the exact revision, preserve upstream license/NOTICE files, identify modifications, and review dependencies before vendoring.

## OpenClaw

- Source: https://github.com/openclaw/openclaw
- License: verify against the upstream repository license and release notices before any code reuse.
- Planned use: reference and benchmark for multi-channel gateway, personal-agent UX, skills, plugins and cross-platform surfaces.
- Current code reuse: none.
- Redistribution obligations if code is reused: audit the exact revision, preserve upstream license/NOTICE files, identify modifications, and review dependencies before vendoring.

## Claude Code

- Source: https://code.claude.com/docs/en/overview
- Status: proprietary product documentation, not an open-source codebase for copying.
- Planned use: black-box product benchmark only.
- Current code reuse: none.

## deja-vu

- Source: https://github.com/vshulcz/deja-vu
- License: MIT License.
- Status: reference and benchmark (Go, stdlib-only session-history index with an MCP surface).
- Ported designs (clean-room Python reimplementation, no code copied): session-source adapter registry, prefix-sharded inverted index, tiered retrieval ladder, untrusted-data framing, manifest cache refresh planning, watermarked peer sync, atomic writer, tool dialect table and deterministic parallel parse.
- Redistribution obligations if code is reused: retain the copyright and MIT permission notice.

## harness-books

- Source: https://github.com/wquguru/harness-books
- License: verify against the upstream repository license and release notices before any code reuse.
- Status: reference only (books on harness engineering; prose and pseudocode, no harness source).
- Ported designs (clean-room Python reimplementation, no code copied): three-valued authorization gate, mandatory ledger closure, circuit-broken recovery ladder, instruction precedence layers and fork isolation.
- Redistribution obligations if code is reused: audit the exact revision, preserve upstream license/NOTICE files, identify modifications, and review dependencies before vendoring.

## claude-code-book

- Source: https://github.com/lintsinghua/claude-code-book
- License: verify against the upstream repository license and release notices before any code reuse (the manuscript states a Creative Commons non-commercial share-alike license; confirmed before any reuse).
- Status: reference only (independent architectural analysis, not Claude Code source).
- Ported designs (clean-room Python reimplementation, no code copied): typed memory records with a bounded index, single-writer trailing extraction queue, shared coordination board with structured task notes and a hook engine.
- Redistribution obligations if code is reused: audit the exact revision and preserve upstream license/NOTICE files.

## wshobson/agents (wshobson-agents)

- Source: https://github.com/wshobson/agents
- License: MIT License (Copyright (c) 2024 Seth Hobson).
- Status: reference and benchmark (Python multi-harness plugin catalog).
- Ported designs (clean-room Python reimplementation, no code copied): tolerant frontmatter, layered composite scoring, registry/disk reconciliation, projection adapters, namespace collision resolution and Elo ranking.
- Redistribution obligations if code is reused: retain the copyright and MIT permission notice.

## qm

- Source: https://github.com/yc-software/qm
- License: MIT License (Copyright (c) 2026 QM contributors).
- Status: reference only (TypeScript multi-agent work platform).
- Ported designs (clean-room Python reimplementation, no code copied): scope namespace isolation, content-addressed blob store, explicit ACL grants, capability tokens, durable leader lease and memory revision compare-and-swap.
- Redistribution obligations if code is reused: retain the copyright and MIT permission notice.

## AI-Builder-Club/skills (ai-builder-club-skills)

- Source: https://github.com/AI-Builder-Club/skills
- License: verify against the upstream repository license and release notices before any code reuse.
- Status: reference only (agentic loop skills and templates).
- Ported designs (clean-room Python reimplementation, no code copied): loop contract, append-only two-layer observation log, file-sentinel completion protocol, verification ledger, deterministic metrics collectors and three-section loop state.
- Redistribution obligations if code is reused: audit the exact revision, preserve upstream license/NOTICE files, identify modifications, and review dependencies before vendoring.

## AMAImedia/harness2 (harness2)

- Source: https://github.com/AMAImedia/harness2
- Upstream work: Harness^2, *Recursive Agent Harnessing for an Open World*, arXiv 2610.14224 (Xu, Chen, CuiZhu, Dalvi Mishra, Ming, Yu, Han, Lee, Pfister). Open-source release by Google; not an officially supported Google product.
- License: Apache License 2.0.
- Status: reference only (recursive agent-harness optimisation framework).
- Ported designs (clean-room Python reimplementation, no code copied): the cue / lesson / evidence triple and evidence-gated lesson storage, per-domain adopted-artifact libraries with prefix retention, anonymised candidate selection with a recorded id map, the machine-readable before/after contrast, and the run-identity budget ledger.
- Deliberately not ported: the LLM harness editor (it would put a model in the deterministic core), unattended library writes (this project requires a named approver before anything becomes recallable), and the third-party benchmark runners, patches and datasets.
- Research copy: `../_research_2026-08/harness2`. Port notes: `docs/HARNESS2_PORT_NOTES.md`.
- Redistribution obligations if code is reused: retain the Apache 2.0 notice; note that the upstream repository bundles third-party benchmark runners under separate upstream licenses.

## NOESIS integration rule

Any future copied or vendored file must be added to the provenance manifest, preserve its original license header where applicable, be accompanied by the complete license/NOTICE text, identify modifications, and pass dependency, secret, AST and security review. Architectural inspiration or a clean-room reimplementation does not require copying upstream source, but its design lineage remains documented here.
