# NOESIS Final Security, Reliability, Packaging and License Audit

**Repository:** `AMAImedia/NOESIS-Harness-Agent-Memory`

**Remote SHA:** `1b4ef5b584125018285dab5b44f8660f5ffc64e1`

**Visibility:** private

## Verified local gates

| Gate | Result | Evidence |
|---|---|---|
| Regression suite | PASS | 234/234 tests on local CPython 3.12.3 |
| Contract benchmark lane | PASS | 10/10 fixed contract cases; 0 failed; 0 not_run in the local lane |
| AST execution audit | PASS | No actual `eval`/`exec` calls detected in core |
| Secret-like scan | PASS with synthetic fixture exception | The only reported private-key pattern is the intentional security holdout corpus fixture |
| Syntax audit | PASS | No syntax errors |
| Git synchronization | PASS | local SHA equals remote SHA |
| Portable source artifact | PASS | ZIP builder emits `PORTABLE_MANIFEST.json`, SHA-256 file entries, and excludes models/secret-like files |
| License/provenance | PASS for audited upstream records | `THIRD_PARTY_NOTICES.md` and `docs/third_party_provenance.json` present; Apache-2.0/MIT obligations remain attached |

## Explicit blockers and non-claims

The active sandbox is CPython 3.12.3. `scripts/verify_python314.py` correctly returns `ok: false` and blocks a Python 3.14 release claim. No native Windows or macOS runner was available, so `.exe`, `.app`, embedded-interpreter, startup/upgrade/uninstall, and native filesystem tests are not verified.

The child execution runtime is a bounded, shell-free process boundary with allowlists, workspace containment, timeout/output limits and fail-closed network behavior. It is **not** claimed to be a hardened OS sandbox. A stronger sandbox adapter remains required before untrusted executable skills can be advertised as production-isolated.

The Web UI and terminal client expose the same versioned session API. Provider invocation remains explicit and Gatekeeper-controlled; this release does not claim autonomous unrestricted model/tool execution. External A/B measurements against Hermes, OpenCode or other products are not run; the benchmark protocol and local contract baseline must not be presented as a world-ranking result.

## Release disposition

This is a **private release candidate for local contract verification**, not a final native desktop release and not evidence that NOESIS is the world's best agent system. The next owner gates are: provide a Python 3.14 environment, provide native Windows/macOS runners or bind a real desktop folder, complete hardened sandbox review, run external benchmark lanes, and explicitly approve any repository governance or visibility change.
