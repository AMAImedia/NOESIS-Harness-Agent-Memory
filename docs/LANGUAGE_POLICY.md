# Project Language Policy

## Primary language

English is the sole primary language for source code, command-line output, shell and batch scripts, API contracts, schemas, configuration, test names, package metadata, the root README, and code-facing documentation. Primary-layer files must contain ASCII-only natural-language text unless a non-ASCII value is required by a protocol, a license, a user payload, or a test fixture.

This policy keeps automation, logs, reproducibility checks, portability tooling, and external review consistent across Linux, macOS, and Windows. It does not change the content language of user data processed by the agent.

## Supplemental language

Russian is supported as an additional documentation layer. Russian documents use an explicit `_RU` filename suffix, including the Russian master checklist and translated runbooks. Supplemental documents may explain the same English contracts, but they are not the normative source for code-facing identifiers, schemas, commands, or machine-readable evidence.

| Layer | Language | Normative for | Filename rule |
|---|---|---|---|
| Primary | English | Code, CLI, APIs, schemas, tests, release metadata, root README, code-facing docs | Default filename |
| Supplemental | Russian | Human-facing translations, Russian checklist, localized runbooks | `_RU.md` suffix |

## Evidence and status vocabulary

Machine-readable and code-facing status values remain English and stable: `passed`, `failed`, `blocked`, `not_run`, `not_started`, and `unknown`. A translation may explain these values, but must not replace them in evidence JSON, APIs, logs, or test assertions.

## Review gate

A release audit must verify that code-facing files contain no unintended Cyrillic text, that all Russian supplemental documents are discoverable through `docs/README.md`, and that links resolve after localization changes. Exceptions must be documented with a path and rationale.
