# Operator Evidence Pipeline

## Purpose

`scripts/run_operator_evidence_pipeline.py` is the bounded operator entry point for external evidence ingestion. It reads a pinned manifest and supplied JSON evidence, writes the readiness matrix and signed aggregate, and can attach the verified aggregate to an optional signed report bundle. It never launches Hermes, OpenCode, DeepSeek Harness, providers, network requests, or child runtimes.

## Artifacts and status

| Artifact | Meaning |
|---|---|
| `external-evidence-readiness.json` | Lane-level readiness matrix from `noesis.external-evidence-readiness.v1`. |
| `signed-external-evidence-aggregate.json` | HMAC-signed deterministic aggregate from `noesis.signed-external-evidence-aggregate.v1`. |
| Optional report ZIP | Signed report bundle containing the aggregate under `external_comparative.signed_evidence_aggregate`. |

The pipeline propagates the aggregate status exactly. `passed` requires all three lanes to pass the existing readiness contract. `not_run`, `blocked`, and `unsupported` remain explicit and are never converted into success or a score. The machine-readable summary includes the fixed `status_vocabulary` (`passed`, `not_run`, `blocked`, `unsupported`), per-lane `status_counts`, and `exit_code`. A pipeline invocation with a non-passed status exits `2`; malformed input or a missing required snapshot for `--report-output` also exits `2` and returns a bounded `blocked` JSON summary.

## Command

```sh
python scripts/run_operator_evidence_pipeline.py \
  --manifest benchmarks/external_ab_manifest_v1.json \
  --evidence reports/hermes.json reports/opencode.json reports/deepseek-harness.json \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --output-dir reports/evidence-pipeline \
  --snapshot reports/operator-snapshot.json \
  --report-output reports/operator-report.zip
```

The command is safe to run when external lanes are unavailable. Missing or unpinned lanes remain machine-readable `not_run` or `blocked`, and the optional report bundle is not created unless a snapshot is explicitly supplied. `automatic_execution=false` and `external_execution_claim=false` are invariant output fields.

After writing the artifact inventory, the pipeline performs an offline verification pass and emits `verification-result.json` with schema `noesis.signed-operator-artifact-verification.v1`. The result binds the inventory digest and check projections, then signs them with HMAC-SHA256. `verification-result.json` is deliberately excluded from `artifact-manifest.json` to avoid a circular digest; it is bound to the inventory by `inventory_digest` and must be verified after transfer. This creates a complete non-executing evidence chain without claiming that any external lane ran.
