# Python 3.14-only migration — 2026-08-17

## Decision

NOESIS-Harness-Agent-Memory is moving to **Python 3.14-only** for the next agent-OS generation. The package metadata now requires `Python >=3.14`, the classifiers advertise Python 3.14 only, the GitHub CI workflow uses a single Python 3.14 test matrix, and README runtime instructions are aligned with this policy.

This is an intentional breaking compatibility decision requested by the owner. It is not yet a claim that native portability is complete: the current sandbox exposes Python 3.12, Python 3.14 is not installed locally, and native Windows/macOS 3.14 verification remains pending.

## Required verification gates

| Gate | Requirement | Status |
|---|---|---|
| Package metadata | `requires-python = ">=3.14"`; classifier only for 3.14 | Implemented |
| CI | Tests, lint and build use Python 3.14 | Implemented in workflow; remote CI verification pending |
| Local runtime | Python 3.14 interpreter available | Not available in current sandbox |
| Full regression | 200+ tests pass under Python 3.14 | Pending interpreter/runner |
| Native Windows | Portable launcher, supervisor, SQLite cleanup, data roots and artifact startup under Python 3.14 | Pending native runner |
| Native macOS arm64 | Same checks under Python 3.14 | Pending native runner |
| Packaging | Self-contained `.exe` and `.app` or documented embedded-runtime strategy | Future phase |
| Release evidence | SHA-256 manifest, interpreter version, platform, test totals and audit output | Future phase |

## Compatibility consequence

The repository no longer promises installation on Python 3.9–3.13. Existing tests may still execute on an older interpreter when launched directly from the source tree, but that is not a supported release configuration. Documentation and CI must not call older versions verified production targets.

## Architectural consequence

Python 3.14 is the runtime for the control plane, agent runtime, provider adapters, executable skill child processes and packaging tools. The core remains stdlib-first. Third-party components can be integrated only behind explicit adapters and must not silently become mandatory dependencies of the memory/security kernel.

## Next implementation step

Before implementing broad execution features, perform a source/license/security audit of Cloudflare OS, Hermes Agent, OpenCode and related projects. Reuse architectural contracts and test ideas where compatible; do not copy code or vendor dependencies until license compatibility, provenance and trust boundaries are recorded.
