# NOESIS Release Review Status — 2026-08-27

**Document:** records the execution of [`RELEASE_REVIEW_CHECKLIST.md`](RELEASE_REVIEW_CHECKLIST.md) stages on this host. This refresh covers stages 5-10 plus a re-run of the test suite and the clean-tree release audit (verification step).
**Host commit:** `9f6a816` (working tree restored to committed state after this session's test run; see New findings).
**Purpose:** status record, not evidence of capability. Lists what was run, what passed, and what remains blocked.
**Interpreter:** `py -3.14` (CPython 3.14.7). Default `python` is 3.11.9 and fails the runtime gate by design.

## Stage results

| # | Stage | Result | Notes |
|---|---|---|---|
| 1 | Runtime gate | PASSED (carried) | 3.14.7; not re-run this session, interpreter unchanged |
| 2 | Local suites | FAIL (re-run) | `py -3.14 -m unittest discover -s tests -q` -> 1152 tests, 1 failure, 18 skipped. Prior "1110 OK" superseded. See New findings for the self-generating-test pollution that causes the failure |
| 3 | Benchmarks | PASSED (recorded) | recall20 acc=1.00, workload20 score=0.8083; not re-run this session |
| 4 | Evidence regeneration | RESOLVED (recorded) | committed evidence byte-stable; not re-run this session |
| 5 | External lanes state (Gate 7) | PARTIAL | Read-only inspection of committed artifacts (below). No external execution performed; no comparative/A-B claim |
| 6 | Native artifact | PARTIAL (re-verified) | `verify_native_artifact.py` exit 0, `evidence_status: development_unsigned`; signature `not_run` (signtool present, cert unavailable); macOS lane `not_run` (no matching host) |
| 7 | Signed evidence pipeline | NOT RUN / BLOCKED | `verify_release_readiness.py` exit 0 (status passed, records `overall_status: blocked`); `verify_release_gate_artifact.py` exit 0 (`gate_status: not_run`); `verify_reproducibility_receipt.py` BLOCKED exit 2 (`--key` required, `NOESIS_EXTERNAL_EVIDENCE_KEY` unset); `verify_operator_artifact_set.py` BLOCKED exit 2 (same) |
| 8 | Transfer audit | NOT RUN / BLOCKED | No transfer performed (read-only task, no external medium). `post_transfer_audit` requires `--key` (unset). Same fail-closed cause as Stage 7 |
| 9 | Link and docs audits | PASSED | `check_markdown_links.py` exit 0 (445 links, 0 missing); `check_json_evidence.py` exit 0 (clean/parseable); `docs_security_audit.py` exit 0 (CLEAN) |
| 10 | Human review | PENDING | Not executable; requires named reviewer + recorded decisions |

### Stage 5 artifact state (read-only, confirmed this session)

| Artifact | Recorded status |
|---|---|
| `docs/PINNED_LANE_MATRIX_314.json` | all lanes `not_run` (deepseek_harness, hermes, opencode) |
| `docs/MODEL_TASK_3LANE_BLOCKERS.json` | present; per-lane blocker records intact (opencode success blocked on key; hermes/deepseek need binaries+keys) |
| `docs/COMPARATIVE_BASELINE_VERSION_SMOKE.json` | `overall_status: passed`, `comparative_ready: true`, `execution_claim: evidence_ingestion_only` (ingestion only, no lane execution) |
| `docs/EXTERNAL_EVIDENCE_READINESS_MATRIX.json` | `overall_status: not_run`, `comparative_ready: false` |

Gate 7 remains open. The version-smoke baseline proves only that signed receipts were accepted by the ingestion contract; it does not prove any external lane produced a task result.

## Hard stop conditions observed

| Condition | Status |
|---|---|
| 1. Not Python 3.14 | CLEAR (3.14.7) |
| 2. Test/benchmark/doc-audit failure | FAIL — full suite 1 failure (`test_bridge_discovery` hermes, full-run only; see New findings). Link/json/docs-security audits are clean |
| 3. Evidence drift | CLEAR (no regeneration this session; committed evidence unchanged) |
| 4. Verifier tampering | CLEAR (Stage 7 blocks are status-driven / key-driven; no tamper, digest mismatch, or schema violation) |
| 5. `native_or_external_execution_claim` true | CLEAR (false across all artifacts) |
| 6. `release_audit.py` exit 2 beyond blocked matrix | CLEAR — on clean tree exit 0, `clean: true`, `working_tree_clean: true`, `secret_like_hits: []` (only `synthetic_fixture_hits` in `security_holdouts.py`, classified synthetic fixture) |
| 7. Parallel release-audit validator rejects | NOT RUN this session (appendix `run_parallel_release_audit_lanes.py` not executed); status unknown, not claimed |
| 8. Missing signed receipts | ACTIVE — external model lanes require operator keys (`DEEPSEEK_API_KEY`/`OPENAI_API_KEY` absent; `NOESIS_EXTERNAL_EVIDENCE_KEY` unset) |

## New findings (this session)

1. **Full-suite test pollution (root cause of Stage 2 failure).** Running `py -3.14 -m unittest discover -s tests -q` as the gate specifies had a side effect: a self-bootstrapping test generated `noesis_harness/self_audit.py` and `tests/test_self_audit.py` (both untracked) and modified `noesis_harness/__init__.py` (added a `self_audit` import block). This (a) dirtied the working tree, (b) inflated the discovered count from the recorded 1110 to 1152, and (c) polluted global module state such that `test_bridge_discovery.BridgeDiscoveryTests.test_ready_hermes_capability_and_matching_model` returns `unavailable` in the full run while passing in isolation. This is a test-hygiene defect (violates the clean-tree and no-mutation discipline), not an external-dependency failure. Restored committed tree: reverted `noesis_harness/__init__.py` and relocated the two generated files to `_archive/noesis_harness_self_audit_2026-08-27.py` and `_archive/tests_test_self_audit_2026-08-27.py`. The defect must be fixed before Stage 2 can be claimed green.

2. **`release_audit.py` import note for Stage 7 verifiers.** `verify_release_readiness.py` / `verify_release_gate_artifact.py` / `verify_reproducibility_receipt.py` / `verify_operator_artifact_set.py` use `from scripts...` imports and require the repo root on `PYTHONPATH` (bare `python scripts/x.py` fails with `ModuleNotFoundError: No module named 'scripts'`). Run as `PYTHONPATH=. py -3.14 scripts/<verifier> ...`. With that, readiness and gate-artifact exit 0 as documented; reproducibility and artifact-set exit 2 solely because `--key` is required and `NOESIS_EXTERNAL_EVIDENCE_KEY` is unset.

### Evidence paths produced this session

- `_temp/native-windows-evidence.json` — Stage 6 `verify_native_artifact.py` output (`evidence_status: development_unsigned`).
- `_temp/unittest.out`, `_temp/unittest.err` — captured full-suite run (1152 tests, 1 failure, 18 skipped).
- `_temp` is gitignored; not committed.

## Re-run verification commands (actual outputs)

```
py -3.14 -m unittest discover -s tests -q
  -> Ran 1152 tests in 214.092s
  -> FAILED (failures=1, skipped=18)
  -> failure: test_bridge_discovery.BridgeDiscoveryTests.test_ready_hermes_capability_and_matching_model
     AssertionError: 'unavailable' != 'ready'   (passes in isolation)

py -3.14 scripts/release_audit.py --root .        # clean tree
  -> exit 0; clean: true; working_tree_clean: true; secret_like_hits: []
  -> synthetic_fixture_hits: [noesis_harness/security_holdouts.py private-key pattern]
  -> external_readiness.overall_status: not_run

py -3.14 scripts/check_markdown_links.py --root .
  -> exit 0; clean: true; local_links: 445; missing_count: 0

py -3.14 scripts/check_json_evidence.py --root .
  -> exit 0; clean: true

py -3.14 scripts/docs_security_audit.py --root .
  -> CLEAN (exit 0)

py -3.14 scripts/verify_native_artifact.py --target windows --artifact dist\noesis-harness.exe --development-unsigned --output _temp\native-windows-evidence.json
  -> exit 0; evidence_status: development_unsigned

PYTHONPATH=. py -3.14 scripts/verify_release_readiness.py --snapshot reports/evidence-pipeline/release-readiness.json
  -> exit 0; status: passed; overall_status: blocked

PYTHONPATH=. py -3.14 scripts/verify_release_gate_artifact.py --artifact reports/evidence-pipeline/release-gate.json
  -> exit 0; gate_status: not_run; status: passed

PYTHONPATH=. py -3.14 scripts/verify_reproducibility_receipt.py --root reports/evidence-pipeline
  -> exit 2; argparse: --key is required (NOESIS_EXTERNAL_EVIDENCE_KEY unset) -> BLOCKED

PYTHONPATH=. py -3.14 scripts/verify_operator_artifact_set.py --root reports/evidence-pipeline
  -> exit 2; argparse: --key is required -> BLOCKED
```

## Resulting status

The project remains an **internal release candidate**. Local gates 1, 3, 4, 9 are verified/carried; Stage 6 native dev-unsigned artifact is re-verified; Stage 7 version-smoke baseline is `passed` (evidence_ingestion_only). Public-claim release remains blocked on:
1. Stage 2 test suite FAIL (1 failure, full-run-only; caused by a self-generating test that writes source) — must be fixed before any regression-free claim.
2. External `model_task` lanes for hermes/deepseek (operator API keys/credits; `NOESIS_EXTERNAL_EVIDENCE_KEY` unset for the signed pipeline).
3. Native signing with a CA-issued certificate (release-grade); macOS host for parity.
4. Human review sign-off on claim-boundary wording.

## Claim boundary

This status record creates no performance-superiority, native-parity, or external-execution claims. All `not_run`/`blocked` lanes remain exactly that. The only permitted outcome is an internal release candidate with boundaries stated.
