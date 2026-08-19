# Signed Evidence Chain Summary

## Purpose

The pipeline emits `chain-summary.json` with schema `noesis.signed-evidence-chain-summary.v1`. It is a compact operator receipt binding the three signed evidence stages:

| Component | Bound field |
|---|---|
| Artifact inventory | `inventory_digest` |
| Signed external aggregate | `aggregate_digest` |
| Signed offline verification result | `verification_result_digest` |

The summary itself has a deterministic `chain_digest` and HMAC-SHA256 signature. It records `automatic_execution=false`, `external_execution_claim=false`, and the claim boundary `offline_evidence_chain_integrity_only`.

## Circular-hash rule

`chain-summary.json` is emitted after the inventory and signed verification result. It is intentionally excluded from `artifact-manifest.json`; otherwise the inventory would hash the summary while the summary would need to bind the inventory digest, creating a circular dependency. The summary remains bound to the inventory through `inventory_digest` and is checked as a separate strict-chain artifact.

## Verification

Strict platform wrappers require all four artifacts: inventory, readiness/aggregate projections, signed verification result, and chain summary. Verification fails closed for missing summary, component digest drift, signature failure, status mismatch, or claim-boundary tampering. Direct Python verification without `--require-signed-result` remains available for legacy artifact sets.

A valid summary proves only that the listed local evidence artifacts form one integrity-consistent offline chain. It does not prove external execution, native host parity, model quality, or worldwide superiority.
