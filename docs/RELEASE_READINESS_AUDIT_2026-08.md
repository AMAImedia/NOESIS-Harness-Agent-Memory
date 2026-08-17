# NOESIS release-readiness audit

Date: 2026-08-17

## Decision

**Status: verification-ready for continued private development; not yet approved for public release.** The pinned coding adapter and cross-agent leakage corpus are implemented and tested. The repository remains private. Dynamic coding-task execution and hardened OS-level isolation are explicitly marked `unavailable`, so this audit does not convert static verification into a sandbox claim.

## Verified checks

| Check | Result | Interpretation |
|---|---:|---|
| Full Python regression | **118/118 passed in 3.097 s** | No regression detected after the new layers |
| Pinned coding adapter tests | **4/4 passed** | Three fixed tasks and fail-soft paths are covered |
| Pinned coding task count | **3** | Revisions pinned to `2026-08-17.1` |
| Static coding pass rate, n=100 | **1.000000** | Fixed valid submissions pass deterministic AST checks |
| Static verification mean/max | **0.279640 / 0.430400 ms** | Local measurement only |
| Dynamic execution status | **unavailable** | No untrusted source is executed |
| Cross-agent leakage cases | **8** | Tenant, recipient, private-scope and proposal boundaries |
| Isolation corpus pass rate, n=100 | **1.000000** | All fixed expected allow/deny cases passed |
| Isolation suite mean/max | **62.058280 / 110.673900 ms** | Includes fresh SQLite broker setup |
| Secret-pattern scan | **clean** | No credential-shaped token or private key in tracked project text |
| Actual Python `eval`/`exec` call scan | **clean** | Corpus strings mentioning the blocked pattern are test data, not calls |
| GitHub repository | **private** | `AMAImedia/NOESIS-Harness-Agent-Memory` |

## Pinned coding adapter

The adapter defines three fixed tasks: `normalize-words-v1`, `safe-join-v1` and `canonical-json-v1`, all at revision `2026-08-17.1`. Verification parses source with Python AST and checks required function names, required calls, required keywords and forbidden calls. It records a SHA-256 artifact digest and returns `failed` for static violations or `unavailable` for unknown tasks and dynamic execution. It never calls `eval`, `exec`, `compile` or a subprocess.

This is a reproducible coding-task gate, not SWE-bench coverage and not an execution sandbox. A later adapter may add a user-supplied isolated runner, but that runner must be separately audited and must preserve the `unavailable` result when hardening is absent.

## Cross-agent leakage corpus

The corpus covers same-tenant message delivery, cross-tenant message denial, recipient-only receive, private-scope write denial, explicit shared-scope proposal, wrong-recipient decision denial, unknown-sender denial and same-agent private-scope write. It tests the existing `IsolationBroker` boundary and does not claim process or memory isolation outside that broker.

The suite deliberately treats explicit proposals as different from implicit memory sharing. Messages are recipient-scoped, cross-tenant sends are denied, private scopes cannot be written by another agent, and only the proposal recipient can decide a pending proposal.

## Release blockers and next gates

| Gate | Status | Required next action |
|---|---|---|
| Public visibility | **Blocked by policy** | Keep repository private until owner explicitly approves public release |
| Dynamic coding execution | **Unavailable** | Add and independently audit an external hardened runner, if needed |
| OS-level sandbox claim | **Unavailable** | Do not claim it without an actual hardened sandbox |
| Branch protection | **Not enabled** | Enable after confirming desired required checks and review policy |
| Larger coding benchmark | **Not yet implemented** | Add a pinned task expansion only after the three-task adapter is stable |
| Long-horizon model comparison | **Not yet implemented** | Run repeated rollouts with fixed model/tools/budget; do not infer from microbenchmarks |

## Reproducibility commands

```text
python -m unittest discover -s tests -v
python benchmarks/coding_isolation_bench.py --n 100
```

The current audit is a local/private engineering gate. It reports measured facts and explicit unavailable capabilities; it does not certify production security, third-party model quality or public-release readiness.
