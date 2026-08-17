# P6-01 Branch Protection Audit — 2026-08-17

## Scope

This note records the current release-gate state for the private repository `AMAImedia/NOESIS-Harness-Agent-Memory`. No branch-protection, visibility, release, or workflow settings were changed during this audit.

## Verified repository state

| Check | Result |
|---|---|
| Repository | `AMAImedia/NOESIS-Harness-Agent-Memory` |
| Visibility | Private (`isPrivate=true`, `visibility=PRIVATE`) |
| Default branch | `main` |
| Local branch | `main`, clean working tree |
| Local/remote SHA | `d3694dd26f4fdc8eacb95428417d8645d12c02a8` on both |
| Remote | `https://github.com/AMAImedia/NOESIS-Harness-Agent-Memory.git` |

## Existing CI gates

The `.github/workflows/ci.yml` workflow runs on pushes and pull requests targeting `main` and `develop`. Its `test` job is a matrix over Python 3.9, 3.10, 3.11 and 3.12 and runs `python -m unittest discover -s tests -v` plus the examples and recall benchmark. Its `lint` job runs `pyflakes` on `noesis_harness/`, `examples/`, `integrations/` and `benchmarks/`. Its `build` job builds the distribution and uploads `dist/*`; it depends on `test`. Its `benchmark` job runs only on pushes to `main`, depends on `test`, and therefore should not be used as a pull-request required check unless the workflow is changed.

The `.github/workflows/publish.yml` workflow is release-only or manually dispatched and publishes to PyPI through the protected `pypi` environment with OIDC. It must not be a branch-protection required check and must not run merely because a pull request is opened.

## Recommended P6-01 required-check policy

Until the repository owner confirms an exact policy, do not enable branch protection. Once confirmed, require the following checks by their exact GitHub check names, subject to one verification pull request: `Tests (Python 3.9)`, `Tests (Python 3.10)`, `Tests (Python 3.11)`, `Tests (Python 3.12)`, `Lint (pyflakes)`, and `Build Distribution`. Do not require `Benchmarks` unless benchmark execution is deliberately moved to pull requests. Do not require `Publish to PyPI`.

Recommended baseline settings are: require a pull request before merging; require one approving review; dismiss stale approvals when new commits are pushed; require conversation resolution; require status checks to pass before merging; require branches to be up to date before merging only if queue time remains acceptable; block force pushes and branch deletion on `main`; and preserve private repository visibility. Admin bypass should remain disabled for normal merges unless the owner explicitly chooses an emergency procedure.

## Owner decisions required

| Decision | Suggested default | Status |
|---|---|---|
| Required approving reviews | 1 | Waiting for owner |
| Dismiss stale reviews | Enabled | Waiting for owner |
| Require conversation resolution | Enabled | Waiting for owner |
| Require branches up to date | Enabled if CI latency is acceptable | Waiting for owner |
| Allow force-push to `main` | Disabled | Waiting for owner |
| Allow branch deletion | Disabled | Waiting for owner |
| Admin bypass | Disabled by default | Waiting for owner |
| Require signed commits | Optional; enable only if owner’s local signing workflow is ready | Waiting for owner |
| Required CI checks | Four test matrix checks + lint + build | Waiting for owner |
| Benchmark required on PR | No, unless workflow trigger is changed | Waiting for owner |
| PyPI publish required on PR | No | Waiting for owner |

## Current platform limitation

A read-only GitHub API check for `branches/main/protection` returned HTTP 403 with the message: `Upgrade to GitHub Pro or make this repository public to enable this feature.` No setting was changed. Therefore, branch protection cannot be enabled for this private repository under the currently available plan. The repository remains private by policy; making it public is a separate owner decision and is not an acceptable workaround without explicit approval.

## Next safe action

The next safe action is to obtain owner confirmation for the table above, keep the policy documented, and inspect one real pull request’s check-run names if/when branch protection becomes available. Applying branch protection is intentionally deferred because the current GitHub plan rejects it and because governance settings must not be changed without owner approval.
