# Third-party notices and integration provenance

NOESIS-Harness-Agent-Memory is not a copy of any upstream agent product. The current private core contains no vendored source from the projects below; they are recorded as architectural references and future optional integration sources.

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

## Claude Code

- Source: https://code.claude.com/docs/en/overview
- Status: proprietary product documentation, not an open-source codebase for copying.
- Planned use: black-box product benchmark only.
- Current code reuse: none.

## NOESIS integration rule

Any future copied or vendored file must be added to the provenance manifest, preserve its original license header where applicable, be accompanied by the complete license/NOTICE text, identify modifications, and pass dependency, secret, AST and security review. Architectural inspiration or a clean-room reimplementation does not require copying upstream source, but its design lineage remains documented here.
