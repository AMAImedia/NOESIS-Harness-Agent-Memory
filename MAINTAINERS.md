# Maintainers

## Active maintainers

| Name | Handle | Role |
|------|--------|------|
| Ilya Bolotnikov | @djbionicl | Project lead, core maintainer, security contact |

## Review expectations

- Core (`noesis_harness/`, `tests/`): every change reviewed by the lead.
- `examples/`, `integrations/`, `benchmarks/`, `docs/`: reviewed by the lead
  before merge; contributors welcome (see `CONTRIBUTING.md`).
- Security reports: handled within 48h (see `SECURITY.md`).

## Bus factor

Currently 1 maintainer. Mitigations:
- `DESIGN.md` and `AGENTS.md` capture every decision so a new maintainer can
  pick up quickly.
- `CHANGELOG.md` records all changes.
- The core is stdlib-only, so no dependency maintenance is needed.

## Escalation

If the lead is unreachable for a security issue for > 7 days, contact
AMAImedia support at support@amaimedia.com.
