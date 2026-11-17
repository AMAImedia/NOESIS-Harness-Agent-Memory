# Project Language Policy

## Primary language

English is the sole language for source code, command-line output, shell and
batch scripts, API contracts, schemas, configuration, test names, package
metadata, the root README, and all documentation. All documentation is written
in English only.

This keeps automation, logs, reproducibility checks, portability tooling, and
external review consistent across Linux, macOS, and Windows, and matches the
language of the codebase (identifiers, commands, machine-readable evidence).

## Operator language selection is a runtime feature

Per project direction, language *selection* (how the agent communicates with the
operator) is a feature of the OS/runtime layer, not a property of the
documentation set. It does NOT require duplicating every document into multiple
languages. Documentation stays single-language (English); if an operator-facing
language preference is implemented, it applies at runtime (e.g. response
rendering), never by maintaining parallel doc trees.

## Evidence and status vocabulary

Machine-readable and code-facing status values remain English and stable:
`passed`, `failed`, `blocked`, `not_run`, `not_started`, `unknown`. A
translation may explain these values, but must not replace them in evidence
JSON, APIs, logs, or test assertions.

## Review gate

A release audit must verify that code-facing files contain no unintended
non-ASCII text, that all documentation references resolve, and that links remain
valid after changes. Exceptions must be documented with a path and rationale.
