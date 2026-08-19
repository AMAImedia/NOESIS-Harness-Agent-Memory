# Signed Evidence Chain Summary

## Назначение

Pipeline создаёт `chain-summary.json` со schema `noesis.signed-evidence-chain-summary.v1`. Это compact operator receipt, связывающий три signed evidence stages:

| Component | Bound field |
|---|---|
| Artifact inventory | `inventory_digest` |
| Signed external aggregate | `aggregate_digest` |
| Signed offline verification result | `verification_result_digest` |

Summary имеет deterministic `chain_digest` и HMAC-SHA256 signature. Он содержит `automatic_execution=false`, `external_execution_claim=false` и claim boundary `offline_evidence_chain_integrity_only`.

## Circular-hash rule

`chain-summary.json` создаётся после inventory и signed verification result. Он намеренно исключён из `artifact-manifest.json`; иначе inventory хешировал бы summary, а summary должен был бы связывать inventory digest, создавая circular dependency. Summary остаётся связанным с inventory через `inventory_digest` и проверяется как отдельный strict-chain artifact.

## Verification

Strict platform wrappers требуют все четыре artifacts: inventory, readiness/aggregate projections, signed verification result и chain summary. Verification fail-closed при missing summary, component digest drift, signature failure, status mismatch или claim-boundary tampering. Direct Python verification без `--require-signed-result` остаётся для legacy artifact sets.

Valid summary доказывает только, что перечисленные local evidence artifacts образуют одну integrity-consistent offline chain. Он не доказывает external execution, native host parity, model quality или worldwide superiority.
