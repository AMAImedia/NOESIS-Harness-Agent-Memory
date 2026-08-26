# NOESIS Release Review Checklist (Gate 8 Preparation)

**Status checkpoint:** 2026-08-26, repository commit `127b28d`
**Normative source:** Gate 8 paragraph of [`PLAN_NOESIS_1.0_MASTER.md`](PLAN_NOESIS_1.0_MASTER.md)
**Runtime policy:** Python 3.14 only for release gates; deterministic core is stdlib-only.
**Operating model:** local-first, private-by-default, human-governed, fail-closed.

## Purpose

This document binds the existing release-relevant artifacts and verifiers into one ordered operator procedure. It defines what to run, what output counts as passing, what the recorded state of this host is, and what may not be claimed when a stage fails. It is a procedure, not evidence: executing it creates no capability, parity, or superiority claims beyond the artifacts it inspects.

## How to read this document

| Convention | Meaning |
|---|---|
| Exit code | `0` = stage passed; `2` = failed, blocked, or fail-closed refusal. |
| Status vocabulary | `passed`, `not_run`, `blocked`, `unsupported`. Non-passed statuses are never converted into success. |
| Signing key | `NOESIS_EXTERNAL_EVIDENCE_KEY` (at least 16 bytes) is operator-supplied, never committed, and required by all HMAC verifiers. |
| Interpreter | Release-gated stages must run under `py -3.14` on this host. The default `python` is 3.11.9 and fails the runtime gate by design. |
| Current known status | Honest recorded state of this host at the checkpoint commit. It is descriptive, not aspirational, and must be refreshed whenever evidence changes. |

Stages are executed in order. A failing stage either aborts the review (see Hard stop conditions) or caps the outcome at internal-review-only. No stage may be skipped and later described as covered.

## Stage overview

| # | Stage | Binding artifacts |
|---|---|---|
| 1 | Runtime gate | Python 3.14 identity |
| 2 | Local suites | unittest discovery, documentation audit tests |
| 3 | Benchmarks | fixed-fixture recall and workload gates |
| 4 | Evidence regeneration | [`MEMORY_QUALITY_EVIDENCE.json`](MEMORY_QUALITY_EVIDENCE.json), [`MULTI_AGENT_WORKLOAD_EVIDENCE.json`](MULTI_AGENT_WORKLOAD_EVIDENCE.json) |
| 5 | External lanes state (Gate 7) | [`PINNED_LANE_MATRIX_314.json`](PINNED_LANE_MATRIX_314.json), [`MODEL_TASK_3LANE_BLOCKERS.json`](MODEL_TASK_3LANE_BLOCKERS.json), [`COMPARATIVE_BASELINE_VERSION_SMOKE.json`](COMPARATIVE_BASELINE_VERSION_SMOKE.json) |
| 6 | Native artifact state (Gate 6) | [`NATIVE_WINDOWS_ARTIFACT_EVIDENCE.json`](NATIVE_WINDOWS_ARTIFACT_EVIDENCE.json), [`CROSS_PLATFORM_RELEASE_GATE_MATRIX.json`](CROSS_PLATFORM_RELEASE_GATE_MATRIX.json) |
| 7 | Signed evidence pipeline | `reports/evidence-pipeline/` bundle plus offline verifiers ([`OPERATOR_EVIDENCE_PIPELINE.md`](OPERATOR_EVIDENCE_PIPELINE.md)) |
| 8 | Transfer audit | post-transfer audit of a copied evidence directory ([`POST_TRANSFER_AUDIT.md`](POST_TRANSFER_AUDIT.md)) |
| 9 | Link and docs audits | markdown links, JSON evidence parseability, docs security |
| 10 | Human review items | license/provenance, README boundaries, localization |

## Stage 1 — Runtime gate

```powershell
py -3.14 scripts\verify_python314.py --json
```

Expected: exit `0` with `"ok": true`, `"required": "3.14.x"`.

Current known status on this host: `py -3.14` is installed and committed artifacts record `3.14.7` ([`reports/evidence-pipeline/release-readiness.json`](../reports/evidence-pipeline/release-readiness.json)). The shell-default `python` is `3.11.9`; invoking the gate with it returns exit `2`, which is correct behavior, not a tool defect.

If this stage fails: no "full Python 3.14 validation" claim may be made, and every downstream stage loses its runtime basis. Re-running later stages under 3.11 does not satisfy this gate.

## Stage 2 — Local test suites

```powershell
py -3.14 -m unittest discover -s tests -q
py -3.14 -m unittest tests.test_documentation_audit -q
```

Expected: exit `0`, no failures or errors.

Current known status on this host: the last recorded full-suite validation bound into a signed snapshot reports `validated_test_count: 1057` under Python `3.14.7` ([`../reports/evidence-pipeline/release-readiness.json`](../reports/evidence-pipeline/release-readiness.json)). The suite was not re-run while this checklist was authored; AGENTS.md requires it green with every change. The bounded recovery discovery runner additionally records `91/91 passed` on the Windows lane in [`RECOVERY_DISCOVERY_EVIDENCE.json`](RECOVERY_DISCOVERY_EVIDENCE.json); a timeout there is classified `incomplete`, never success.

If this stage fails: no regression-free release candidate claim may be made, and the readiness snapshot regenerated in Stage 7 would carry a stale or false test count.

## Stage 3 — Deterministic benchmarks

```powershell
py -3.14 benchmarks\recall20.py
py -3.14 benchmarks\workload20.py
```

Expected: exit `0` from both. `recall20` requires accuracy of at least `0.80` on its fixed 20-query fixture; `workload20` folds the fixed rubric evaluator with one bounded multi-lane replay.

Current known status on this host: deterministic fixtures with no network and no wall-clock inputs. The committed parallel audit lanes record workload digest `sha256:03292a7c...76909` as `passed` in [`PARALLEL_RELEASE_AUDIT_EVIDENCE.json`](PARALLEL_RELEASE_AUDIT_EVIDENCE.json). Not re-run during authoring.

If this stage fails: no local benchmark-parity claim may be made (see [`P13_LOCAL_BENCHMARK_PARITY_PY314_EVIDENCE.json`](P13_LOCAL_BENCHMARK_PARITY_PY314_EVIDENCE.json)); deterministic-evidence wording must be removed from release notes until green.

## Stage 4 — Evidence regeneration and byte stability

Regenerate the two deterministic local evidence documents and require byte-identical results:

```sh
make evidence-local
git diff --exit-code -- docs/MEMORY_QUALITY_EVIDENCE.json docs/MULTI_AGENT_WORKLOAD_EVIDENCE.json
```

The make target expands to `python -m scripts.run_memory_quality_evidence > docs/MEMORY_QUALITY_EVIDENCE.json` and `python -m scripts.run_workload_evidence --output docs/MULTI_AGENT_WORKLOAD_EVIDENCE.json`. On Windows, reproduce the redirection with a byte-faithful shell or `PYTHONUTF8=1`; PowerShell 5.1 `>` rewrites the encoding and would manufacture drift.

Optional honest-host sandbox report (stdout only, never treated as native parity):

```powershell
py -3.14 -m scripts.run_sandbox_conformance
```

Expected: regeneration produces zero diff; conformance prints schema `noesis.sandbox-conformance.v2` with explicit non-passed records for unavailable native execution paths.

Current known status on this host: both committed evidence documents are byte-stable by construction (no wall-clock fields); the Windows backend conformance records remain command-inspection-level, consistent with [`NATIVE_EVIDENCE_HONESTY_GATE.md`](NATIVE_EVIDENCE_HONESTY_GATE.md).

If this stage fails (diff non-zero): the committed evidence no longer matches the code. Release review must stop until the artifact is regenerated and committed or the code change is reverted. No "deterministic evidence" claim survives a drift.

## Stage 5 — External lanes state (Gate 7)

Operator re-pin and planning commands. These regenerate committed planning artifacts and were not executed during authoring; run them only when intentionally re-pinning:

```sh
python scripts/pin_external_revisions.py --output docs/PINNED_EXTERNAL_MANIFEST_DRAFT.json
python scripts/pinned_lane_orchestrator.py \
  --manifest docs/PINNED_EXTERNAL_MANIFEST_DRAFT.json \
  --workspace _temp/pinned-ws \
  --output docs/PINNED_LANE_MATRIX_314.json
```

Actual lane execution remains a separate operator-approved pinned-runner operation gated by `noesis.external-approval.v1` receipts (see [`PINNED_LANE_OPERATOR_PREFLIGHT.md`](PINNED_LANE_OPERATOR_PREFLIGHT.md)). Signed receipts, once acquired, are ingested offline by `scripts/aggregate_external_evidence.py` without launching anything.

Recorded state (read, do not regenerate casually):

| Artifact | Recorded status |
|---|---|
| [`PINNED_LANE_MATRIX_314.json`](PINNED_LANE_MATRIX_314.json) | readiness `overall_status: blocked`, `comparative_ready: false`; deepseek_harness `not_run` (unavailable, revision pinned), hermes `not_run` (missing exact revision), opencode ready for operator approval, execution `not_started` |
| [`MODEL_TASK_3LANE_BLOCKERS.json`](MODEL_TASK_3LANE_BLOCKERS.json) | opencode `passed` with `task_success: 1.0`; hermes `blocked` (binary quarantined by antivirus; `OPENAI_API_KEY` absent); deepseek_harness `blocked` (DSH profile stack absent; `DEEPSEEK_API_KEY` absent). Unblock paths are listed per lane in the artifact |
| [`EXTERNAL_EVIDENCE_READINESS_MATRIX.json`](EXTERNAL_EVIDENCE_READINESS_MATRIX.json) | `overall_status: not_run`, `comparative_ready: false` |
| [`COMPARATIVE_BASELINE_VERSION_SMOKE.json`](COMPARATIVE_BASELINE_VERSION_SMOKE.json) | signed aggregate `overall_status: passed` with `execution_claim: evidence_ingestion_only` |

The baseline smoke aggregate proves only that three signed receipts were accepted by the ingestion contract. It does not prove that any external lane produced a task result during aggregation.

If this stage shows anything other than all-required-lanes `passed` with one protocol fingerprint: no comparative ranking, no A/B advantage, and no external-execution claim may be made. Gate 7 remains open.

## Stage 6 — Native artifact state (Gate 6)

Offline metadata verification of the local development artifact:

```powershell
py -3.14 scripts\verify_native_artifact.py --target windows --artifact dist\noesis-harness.exe --development-unsigned --output _temp\native-windows-evidence.json
```

Expected: exit `0` means shape, host binding, and SHA-256 are internally consistent for an explicitly unsigned development artifact. It is not a signing or parity statement.

Recorded state on this host ([`NATIVE_WINDOWS_ARTIFACT_EVIDENCE.json`](NATIVE_WINDOWS_ARTIFACT_EVIDENCE.json)):

| Field | Value |
|---|---|
| `evidence_status` | `development_unsigned` |
| `signature.status` | `not_run` (`signtool` present, certificate unavailable) |
| SHA-256 | `558ddfe906a5bb1ad98686597d5927a3944191ac03c29e667af57527a4579a48` |
| host | windows, AMD64, Python 3.14.7, `platform_ok` and `python_ok` true |
| macOS lane | `not_run` (no matching host) |

Native parity bundles ([`NATIVE_PARITY_OPERATOR_RUNBOOK.md`](NATIVE_PARITY_OPERATOR_RUNBOOK.md): `scripts/run_native_parity.ps1`, `scripts/run_native_parity_macos.sh`) remain unexecuted in the machine-readable matrix; the Windows host exists, but no recorded bundle run has been validated by `scripts/validate_native_parity.py`.

If this stage is used to claim more than recorded: prohibited. No signed or notarized artifact claim, no native Windows/macOS parity claim, and no "production binary" wording may be made while `signature.status` is `not_run` and the parity matrix rows are `not_run`.

## Stage 7 — Signed evidence pipeline (regeneration plus offline verification)

Canonical bounded regeneration (writes `reports/evidence-pipeline/`; exits `2` while lanes are non-passed, which is the documented propagation rule):

```sh
python scripts/run_operator_evidence_pipeline.py \
  --manifest benchmarks/external_ab_manifest_v1.json \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --output-dir reports/evidence-pipeline \
  --readiness-test-count 1057 \
  --readiness-python-version 3.14.7 \
  --native-status not_run \
  --external-status not_run
```

Offline verifiers against the committed bundle:

```sh
python scripts/verify_release_readiness.py --snapshot reports/evidence-pipeline/release-readiness.json
python scripts/verify_release_gate_artifact.py --artifact reports/evidence-pipeline/release-gate.json
python scripts/verify_reproducibility_receipt.py --root reports/evidence-pipeline --key "$NOESIS_EXTERNAL_EVIDENCE_KEY"
python scripts/verify_operator_artifact_set.py --root reports/evidence-pipeline --key "$NOESIS_EXTERNAL_EVIDENCE_KEY"
./scripts/post_transfer_audit.sh --root reports/evidence-pipeline --key "$NOESIS_EXTERNAL_EVIDENCE_KEY"
./scripts/release_gate.sh --root reports/evidence-pipeline --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" --snapshot reports/evidence-pipeline/release-readiness.json
```

Expected current outcomes, and why they differ:

| Verifier | Expected today | Reason |
|---|---|---|
| `verify_release_readiness.py` | exit `0` | Snapshot is internally consistent; it honestly records `overall_status: blocked` with blockers `matching_native_windows_macos_hosts_required`, `pinned_external_lane_receipts_required` |
| `verify_release_gate_artifact.py` | exit `0` | Artifact digest and claim boundary valid; recorded `gate_status` stays `not_run` |
| `verify_reproducibility_receipt.py` | exit `0` with the original key; `2` otherwise | Digest chain binds only under the operator key that signed it |
| `verify_operator_artifact_set.py` (strict wrapper) | exit `2` | Readiness matrix is `not_run`, so the full-chain requirement correctly refuses |
| `post_transfer_audit.sh` | exit `2`, `failed_stage: artifact_chain` | Same fail-closed cause; composition and reproducibility stages are sound |
| `release_gate.sh` | exit `2` | First stage inherits the blocked chain |

These failures are the recorded Gate 6/7 gap, not verifier malfunctions. They cap the review at internal-release-candidate status. See [`RELEASE_READINESS_VERIFIER.md`](RELEASE_READINESS_VERIFIER.md), [`REPRODUCIBILITY_VERIFIER.md`](REPRODUCIBILITY_VERIFIER.md), [`OFFLINE_OPERATOR_ARTIFACT_VERIFIER.md`](OFFLINE_OPERATOR_ARTIFACT_VERIFIER.md), and [`RELEASE_GATE.md`](RELEASE_GATE.md).

If any verifier reports tampering, digest mismatch, or schema violation instead of a status-driven block: treat it as a hard stop condition below, not as expected behavior.

## Stage 8 — Transfer audit

Copy `reports/evidence-pipeline/` to the receiving host or medium, then re-verify the copy without regenerating:

```powershell
.\scripts\post_transfer_audit.ps1 `
  --root <copied-dir> `
  --key $env:NOESIS_EXTERNAL_EVIDENCE_KEY
.\scripts\verify_operator_artifacts.ps1 --root <copied-dir> --key $env:NOESIS_EXTERNAL_EVIDENCE_KEY
```

Expected: identical outcomes to Stage 7 on the same key. A successful copy changes no statuses; transfer proves integrity of composition and digests only ([`PORTABLE_TRANSFER_AUDIT.md`](PORTABLE_TRANSFER_AUDIT.md)). Unexpected extra files in the directory fail composition closed by design.

If this stage fails on an intact copy with the original key: hard stop. Investigate before any further distribution.

## Stage 9 — Link and docs audits

```sh
python scripts/check_markdown_links.py --root .
python scripts/check_json_evidence.py --root .
python scripts/docs_security_audit.py --root .
```

Expected: exit `0` from all three (`clean: true`, `CLEAN`). Additionally `py -3.14 -m unittest tests.test_documentation_audit -q` must pass (covered in Stage 2).

Localization audit: every English-primary release document must have its Russian supplemental mirror under `locales/ru/` with commands kept verbatim. The mirror of this document is [`locales/ru/RELEASE_REVIEW_CHECKLIST_RU.md`](locales/ru/RELEASE_REVIEW_CHECKLIST_RU.md); the normative plan mirror is [`locales/ru/PLAN_NOESIS_1.0_MASTER_RU.md`](locales/ru/PLAN_NOESIS_1.0_MASTER_RU.md).

Current known status on this host: link and docs-security audits were clean at authoring time; the localization pair was created together with this document.

If any audit fails: broken links, unparseable evidence JSON, or unsafe copy/paste examples block documentation release. Fix sources rather than weakening the auditors.

## Stage 10 — Human review items

Not executable; each item requires a named reviewer and a recorded decision.

| Item | Source material |
|---|---|
| License and third-party attribution obligations | [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md), [`third_party_provenance.json`](third_party_provenance.json), provenance discipline in [`../RESEARCH_DAIGEST.md`](../RESEARCH_DAIGEST.md) |
| README states verified capabilities and unresolved boundaries | repository `README.md`; honesty criterion in [`PLAN_NOESIS_1.0_MASTER.md`](PLAN_NOESIS_1.0_MASTER.md) |
| Claim progress matrix agrees with recorded artifacts | [`CLAIMS_PROGRESS_MATRIX.json`](CLAIMS_PROGRESS_MATRIX.json), roadmap reconciliation guard [`ROADMAP_RECONCILIATION_EVIDENCE.json`](ROADMAP_RECONCILIATION_EVIDENCE.json) |
| Localization completeness for changed docs | `locales/ru/` mirrors |
| Changelog and release metadata currency | `CHANGELOG.md`, packaging metadata |
| No wording beyond recorded evidence | reviewer compares every public sentence against artifacts listed in Stages 4-8 |

A human review pass may reject a release even when every executable stage passes. It may never approve wording that the artifacts do not support.

## Hard stop conditions

Release review must abort immediately, and no partial credit carries forward, when any of the following occurs:

1. Stage 1 fails: the active interpreter is not Python 3.14.
2. Any unit test, benchmark, or documentation-audit test fails (Stages 2, 3, 9).
3. Deterministic evidence regeneration drifts from committed bytes (Stage 4).
4. Any verifier reports tampering, signature failure, digest mismatch, schema violation, or unexpected transfer composition (Stages 7, 8), as opposed to an honest non-passed status.
5. `native_or_external_execution_claim` is `true` anywhere, or any `not_run`/`blocked` lane appears as passed in prose or artifacts.
6. `scripts/release_audit.py` exits `2` for reasons beyond the expected blocked external matrix: secret-like hits, `eval`/`exec` usage, syntax errors, dirty working tree, roadmap inconsistency, or readiness-artifact errors.
7. The parallel release-audit validator rejects a fresh report (including `working_tree_clean` false after the review edits are committed).
8. Required signed receipts are missing where the strict chain demands them, or the operator key cannot reproduce recorded digests.
9. A human review item is unresolved or a reviewer records disagreement with the claim boundary.

Known current blockers matching these conditions on this host: dirty working tree (two modified docs, two untracked appcontainer files), external readiness `not_run`, native signature `not_run`. Until each is resolved, the only permitted review outcome is an internal release candidate with boundaries stated.

## Clean-tree release audit appendix

After committing all review changes, run the read-only audit and the parallel lanes:

```sh
python scripts/release_audit.py --root .
python scripts/run_parallel_release_audit_lanes.py --output docs/PARALLEL_RELEASE_AUDIT_EVIDENCE.json
python scripts/validate_parallel_release_audit_report.py docs/PARALLEL_RELEASE_AUDIT_EVIDENCE.json
```

Expected: exit `0` from all three; the validator requires five passed lanes, a clean working tree, zero secrets, and digest-valid workload evidence ([`RELEASE_AUDIT_EXTERNAL_READINESS.md`](RELEASE_AUDIT_EXTERNAL_READINESS.md)). An allowed `--remote --remote-branch <branch>` variant adds opt-in remote SHA parity; omitting it performs no network operation.

## Claim boundary

This checklist is procedural. Completing it, in whole or in part, creates no performance-superiority claim, no native Windows/macOS parity claim, and no external-execution claim beyond what the referenced signed artifacts individually record. `not_run` and `blocked` statuses remain exactly that regardless of how many stages pass. The governing honesty criterion, including the condition under which a world-class-superiority hypothesis could become testable, is defined solely by [`PLAN_NOESIS_1.0_MASTER.md`](PLAN_NOESIS_1.0_MASTER.md) and its Russian supplemental localization [`locales/ru/PLAN_NOESIS_1.0_MASTER_RU.md`](locales/ru/PLAN_NOESIS_1.0_MASTER_RU.md).
