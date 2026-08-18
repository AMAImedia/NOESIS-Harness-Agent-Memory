# GitHub Free private repositories — limits and NOESIS next tasks

**Дата:** 2026-08-17  
**Repository:** `AMAImedia/NOESIS-Harness-Agent-Memory`  
**Policy:** repository remains private; no visibility or billing changes were made

## Executive summary

The current GitHub Free plan does not block the core NOESIS work. All code, tests, static AST verification, local benchmarks, documentation, release-audit scripts and normal authenticated pushes can continue. The main governance limitation is that **protected branches, required pull-request reviewers, Code Owners and related advanced private-repository controls are GitHub Pro features for personal accounts** [1]. The API check already confirmed that branch protection is unavailable for this private repository under the current plan.

The practical strategy is therefore to continue building and verifying NOESIS locally and in CI, while treating branch protection, private deployment environments and advanced security automation as optional platform gates rather than core engineering blockers.

## Tasks that can continue without paid GitHub features

| Area | Tasks available now | Evidence of completion |
|---|---|---|
| Core engineering | Continue P4/P5 hardening, memory recovery, best-state protection, skill rollback, bridge adapters and local-first control-plane work | Focused tests, full regression, AST audit, benchmark and local commit |
| Static security | Expand security holdout and cross-agent leakage corpus; scan secrets and forbidden imports; maintain no `eval`/`exec` contract | Deterministic corpus pass rates and audit report |
| CI | Use GitHub Actions within the Free quota; the existing matrix can run on pull requests and pushes | CI check results; 2,000 standard-runner minutes/month for personal GitHub Free accounts [1] [2] |
| Documentation | Update Russian master checklist, architecture docs, decision memos, README and release-readiness evidence | Markdown review and private push |
| Packaging | Build distributions, run `Build Distribution`, generate local portable artifacts and checksum manifests | CI artifact or local hash manifest; artifact storage must stay within the shared allowance |
| Native verification | Use a user-owned Windows/macOS runner or local machines; no GitHub-hosted paid runner is required | Native smoke-test logs and platform evidence |
| Collaboration | Add collaborators if needed; GitHub Free allows unlimited collaborators on personal public and private repositories [3] | Access review and least-privilege permissions |
| Releases | Create GitHub Releases and attach appropriately sized binaries; GitHub documents releases as an option for distributing large binaries [4] | Release manifest and checksum verification |

## Tasks blocked or constrained by the current GitHub plan

| Feature or task | Current status | Workaround without changing visibility |
|---|---|---|
| Branch protection on private `main` | Blocked; API returned HTTP 403 requiring Pro or a public repository | Keep policy documented, use local pre-push checks and CI, enable later only after plan/visibility decision |
| Required PR reviewers / multiple reviewers / Code Owners for private repository | GitHub Pro feature for personal accounts [1] | Use documented owner review procedure and CODEOWNERS file as documentation, but it will not enforce merges until a compatible plan is available |
| Private GitHub Actions environments with protection rules | GitHub Free users can configure environments only for public repositories; private environments require GitHub Pro or GitHub Team [5] | Keep PyPI publishing disabled except manual/release workflow; use local approval and external secret management |
| Deployment protection rules for private repositories | Listed for public repositories on Free; private deployment protection requires a higher plan [1] [5] | Do not treat GitHub environment approval as a security boundary in the private Free repository |
| Secret Protection / secret-scanning alerts for this personal private repository | The documented free enablement path is for free public repositories; organization-owned repositories use Secret Protection [6] | Continue `scripts/release_audit.py`, local secret-pattern scanning, history scrub and token rotation discipline |
| Private GitHub Pages | Not available for a personal Free private repository; private Pages requires an organization with Enterprise Cloud [1] | Use the local control plane, an external private host or a future public documentation repository only after approval |
| GitHub-hosted Windows/macOS CI at scale | Consumes the private Actions quota and Windows/macOS minutes are metered; usage beyond quota is blocked without a payment method or billed with one [2] | Use Linux CI for deterministic checks and local/user-owned Windows/macOS runners for native verification |
| Large model files in normal Git | Files above 100 MiB are blocked; files above 50 MiB produce a warning; GitHub recommends repositories below 1 GB and strongly below 5 GB [4] | Keep model weights/datasets outside the code repository, use Hugging Face or approved object storage, and store only manifests/checksums |
| Git LFS heavy usage | LFS has plan quotas for storage and bandwidth; large model repositories can exhaust quota | Use Hugging Face for model artifacts and keep Git LFS limited to genuinely necessary files; verify current LFS quota before upload |
| Private GitHub Packages at scale | Free accounts receive 500 MB GitHub Packages storage; private package usage beyond the included quota is blocked without payment or controlled by budgets [1] [2] [7] | Do not publish model artifacts or large wheels to Packages; keep packages minimal and clean old artifacts |
| Codespaces for heavy development | Free personal accounts include 120 core hours and 15 GB storage per month [1] | Develop locally; do not use Codespaces for model builds or long-running tests |

## Recommended next execution order

The first next task is **continuous hardening without GitHub governance dependencies**: expand the security holdout corpus, add regression cases for credential-like strings and cross-agent scope confusion, and keep the AST-only coding adapter fail-soft. This produces real security improvements and requires no paid GitHub feature.

The second task is **local/native verification tooling**. Add deterministic scripts that can be executed on Windows and macOS by the owner, record platform information, verify loopback binding, data-root separation, clean shutdown and SHA-256 manifests, and store only compact evidence in Git. This avoids consuming paid GitHub-hosted macOS minutes.

The third task is **CI cost reduction and evidence quality**. Keep the existing matrix, but add bounded timeouts, avoid unnecessary artifact retention, and ensure the benchmark remains push-to-main or manually triggered rather than a mandatory pull-request job. The current workflow already keeps `Publish to PyPI` separate from ordinary CI and should preserve that boundary.

The fourth task is **portable release documentation**. Create a release manifest format containing commit SHA, Python version, platform, test totals, benchmark identifiers and artifact hashes. This can be reviewed and pushed to the private repository without branch protection.

Branch protection remains a governance task, not an engineering blocker. It should be revisited only after the owner decides whether to upgrade the personal account, move the repository to a suitable organization plan, or retain the current private Free setup with documented manual review.

## Practical security warning

A private repository on GitHub Free is not equivalent to a fully governed enterprise repository. Private visibility limits who can view the source, but it does not provide enforced review gates, protected branches, private deployment approvals or complete Advanced Security coverage. NOESIS must therefore keep its own local security contract: deny-by-default execution, static AST verification, secret redaction, loopback-only networking, explicit authentication for LAN mode, transactional skill imports, best-state verification and rollback/recovery tests.

## References

[1]: https://docs.github.com/get-started/learning-about-github/githubs-products "GitHub's plans"

[2]: https://docs.github.com/billing/managing-billing-for-github-actions/about-billing-for-github-actions "GitHub Actions billing"

[3]: https://docs.github.com/articles/inviting-collaborators-to-a-personal-repository "Inviting collaborators to a personal repository"

[4]: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github "About large files on GitHub"

[5]: https://docs.github.com/actions/deployment/targeting-different-environments/using-environments-for-deployment "Managing environments for deployment"

[6]: https://docs.github.com/en/code-security/how-tos/secure-your-secrets/detect-secret-leaks/enable-secret-scanning "Enabling secret scanning for your repository"

[7]: https://docs.github.com/en/packages/learn-github-packages/introduction-to-github-packages "Introduction to GitHub Packages"
