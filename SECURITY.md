# Security Policy

## Reporting a Vulnerability

This project stores agent state (event logs, memory, coordination leases).
A vulnerability in the storage layer could expose agent conversation data.

Please report vulnerabilities privately - do NOT open a public issue:

- Email: djbionicl@amaimedia.com
- Subject prefix: `[NOESIS-SEC]`

You should receive a response within 48 hours. If you do not, follow up.

## Scope

In scope:
- `noesis_harness/` - event store, memory, coordination (SQLite, JSONL).
- File permission handling (WAL files, refs/, offload).
- Idempotency guards (fingerprint collisions, lease bypass).

Out of scope:
- Application code that uses the framework (BotFarm, etc.).
- LLM model weights or prompts.
- Third-party dependencies (there are none in the core - that is a feature).

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | yes |
| 0.1.x   | yes (security fixes only) |
| < 0.1   | no |

## Security design notes

- Append-only JSONL: a partial write loses only the last line (crash-safe).
- SQLite WAL: readers and one writer coexist; busy_timeout waits, never corrupts.
- Idempotent append by fingerprint: a double-send cannot duplicate events.
- TTL leases: a crashed agent cannot strand a task forever.
- Fail-soft everywhere: a locked DB or missing module degrades to a no-op,
  never a crash or a data leak.
