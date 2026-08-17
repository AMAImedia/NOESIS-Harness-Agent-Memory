# Governance

This project is a small, focused, local-first agent framework. Governance is
deliberately lightweight but explicit.

## Maintainer

- **Ilya Bolotnikov** (@djbionicl) - AMAImedia - project lead and sole
  maintainer. Responsible for:
  - Merging pull requests to `main`.
  - Releasing versions (SemVer).
  - The core `noesis_harness/` package and `tests/`.
  - Security response (see `SECURITY.md`).

## Decision process

- **Small changes** (one file, one job): maintainer reviews and merges.
- **Architecture changes** (new module, schema change, API break): opened as
  a design issue first, discussed in `DESIGN.md` terms, then implemented.
- **Dependency additions to the core**: forbidden by design (see `AGENTS.md`).
  A proposal to add a dependency must first change `AGENTS.md` and `DESIGN.md`.

## Versioning

- Semantic Versioning. Breaking API changes bump the major (or minor while
  < 1.0). Additions bump minor. Fixes bump patch.
- Every release gets a `CHANGELOG.md` entry and a git tag.

## Community

- Issues and discussions on GitHub.
- Code of Conduct applies everywhere (see `CODE_OF_CONDUCT.md`).

## Funding

- This project is funded by AMAImedia (no corporate sponsors).
- `FUNDING.yml` lists the funding platform when it is live.
