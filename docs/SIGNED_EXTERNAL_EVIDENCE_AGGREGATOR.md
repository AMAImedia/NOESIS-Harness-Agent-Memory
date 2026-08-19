# Signed External Evidence Aggregator

## Purpose

`scripts/aggregate_external_evidence.py` produces a deterministic, signed aggregate of receipt-backed readiness evidence for exactly three required lanes: `hermes`, `opencode`, and `deepseek_harness`. It is an ingestion and verification component only. It does not install, launch, contact, or control any external executable.

## Contract

The aggregator first delegates lane validation to `noesis.external-evidence-readiness.v1`. Each accepted record must have a valid HMAC envelope, exact pinned revision, matching environment digest when required, deterministic receipt identity, and a shared protocol fingerprint. Duplicate system records, duplicate receipt IDs, stale receipts, signature failures, revision drift, environment drift, unsupported execution, and protocol conflicts remain explicit lane or global statuses.

The output schema is `noesis.signed-external-evidence-aggregate.v1`. Evidence is canonically ordered by lane identity, revision, receipt ID, and record digest before `evidence_digest` and the signed aggregate are calculated. The aggregate includes the manifest digest, evidence digest, readiness matrix digest, all required lane projections, global checks, and a HMAC-SHA256 signature. Verification fails closed for schema drift, digest mismatch, signature mismatch, lane identity mismatch, or any attempt to set `native_or_external_execution_claim=true`.

| Status | Meaning |
|---|---|
| `passed` | All three lanes passed readiness verification. This is signed evidence aggregation, not a quality or superiority claim. |
| `not_run` | A required revision or execution evidence is absent without a pinned contradictory record. |
| `blocked` | A pinned lane or global identity/security check failed. |
| `unsupported` | The lane explicitly reports that the required execution mode is unsupported. |

## Claim boundary

A `passed` aggregate proves only that the submitted evidence was internally verified against the declared manifest and signing key. It does not prove that the current host ran Hermes, OpenCode, or DeepSeek Harness, and it does not rank systems. Comparative scoring requires the separate case-level evaluator, independent scoring rules, repeated runs, and operator-approved evidence artifacts. The repository's current external artifact remains `not_run` until matching pinned environments produce receipts.

## CLI

```sh
python scripts/aggregate_external_evidence.py \
  --manifest benchmarks/external_ab_manifest_v1.json \
  --evidence reports/hermes.json reports/opencode.json reports/deepseek-harness.json \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --output reports/signed-external-evidence-aggregate.json
```

A non-passed aggregate exits with code `2`. The command writes no executable configuration and never infers missing evidence as success.
