# Operator Evidence Pipeline

## Purpose

`scripts/run_operator_evidence_pipeline.py` is the bounded operator entry point for external evidence ingestion. It reads a pinned manifest and supplied JSON evidence, writes the readiness matrix and signed aggregate, and can attach the verified aggregate to an optional signed report bundle. It never launches Hermes, OpenCode, DeepSeek Harness, providers, network requests, or child runtimes.

## Artifacts and status

| Artifact | Meaning |
|---|---|
| `external-evidence-readiness.json` | Lane-level readiness matrix from `noesis.external-evidence-readiness.v1`. |
| `signed-external-evidence-aggregate.json` | HMAC-signed deterministic aggregate from `noesis.signed-external-evidence-aggregate.v1`. |
| Optional report ZIP | Signed report bundle containing the aggregate under `external_comparative.signed_evidence_aggregate`. |
| Optional readiness bundle | `release-readiness.json`, `release-gate.json`, and `signed-readiness-receipt.json`, generated when readiness test count and Python version are supplied. |
| Execution conformance | `execution-conformance.json`, generated with the readiness bundle; local replay remains `not_run` unless `--conformance-replay` supplies a verified replay result. |

The pipeline propagates the aggregate status exactly. `passed` requires all three lanes to pass the existing readiness contract. `not_run`, `blocked`, and `unsupported` remain explicit and are never converted into success or a score. The machine-readable summary includes the fixed `status_vocabulary` (`passed`, `not_run`, `blocked`, `unsupported`), per-lane `status_counts`, and `exit_code`. A pipeline invocation with a non-passed status exits `2`; malformed input or a missing required snapshot for `--report-output` also exits `2` and returns a bounded `blocked` JSON summary.

## Command

```sh
python scripts/run_operator_evidence_pipeline.py \
  --manifest benchmarks/external_ab_manifest_v1.json \
  --evidence reports/hermes.json reports/opencode.json reports/deepseek-harness.json \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --output-dir reports/evidence-pipeline \
  --snapshot reports/operator-snapshot.json \
  --report-output reports/operator-report.zip \
  --readiness-test-count 636 \
  --readiness-python-version 3.14.7 \
  --native-status not_run \
  --external-status not_run \
  --conformance-replay reports/evidence-replay/replay-result.json
```

The command is safe to run when external lanes are unavailable. Missing or unpinned lanes remain machine-readable `not_run` or `blocked`, and the optional report bundle is not created unless a snapshot is explicitly supplied. `automatic_execution=false` and `external_execution_claim=false` are invariant output fields.

When `--readiness-test-count` and `--readiness-python-version` are supplied, the pipeline additionally emits `release-readiness.json`, `release-gate.json`, and `signed-readiness-receipt.json`. The receipt binds the snapshot digest, gate artifact digest, readiness status, test count, Python version, and HMAC-SHA256 signature. Native and external statuses remain explicit; `not_run` never becomes `passed`. After writing the artifact inventory, the pipeline performs an offline verification pass and emits `verification-result.json` with schema `noesis.signed-operator-artifact-verification.v1`. The result binds the inventory digest and check projections, then signs them with HMAC-SHA256. The generated `execution-conformance.json` is an optional transfer artifact and is excluded from `artifact-manifest.json` to avoid circular digests. Without `--conformance-replay`, its local class is explicitly `not_run`; it does not infer replay success from pipeline generation. These generated summary artifacts are verified by the strict post-transfer audit. This creates a complete non-executing evidence chain without claiming that any external lane or native host ran.
