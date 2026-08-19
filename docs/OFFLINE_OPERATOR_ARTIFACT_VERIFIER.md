# Offline Operator Artifact Verifier

## Purpose

`scripts/verify_operator_artifact_set.py` verifies a transferred pipeline artifact directory without executing any artifact content. It checks `artifact-manifest.json`, every inventory-listed file, the readiness matrix, the signed external aggregate, and an optional report bundle.

## Cross-artifact checks

The verifier performs these checks in order:

1. It verifies the signed artifact inventory and all listed file digests under the supplied root.
2. It requires the readiness matrix and signed aggregate to exist and have their expected schemas.
3. It verifies the aggregate signature and requires its `matrix_digest` to equal the readiness matrix digest.
4. If `--report` is supplied, it requires the report ZIP to be inside the artifact root and verifies it with the operator key.
5. It returns the aggregate readiness status while preserving `comparative_ready=false` and `external_execution_claim=false` when the evidence does not support a comparative claim.

Any schema, signature, digest, missing-file, traversal, report-path, or cross-artifact mismatch is `blocked` and exits with code `2`. Verification reads JSON and ZIP metadata only; it does not import, launch, or interpret artifact content.

## Command

```sh
python scripts/verify_operator_artifact_set.py \
  --root reports/evidence-pipeline \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --report reports/evidence-pipeline/operator-report.zip
```

A successful result has `status=passed`, `checks.inventory.status=passed`, `checks.aggregate.status=passed`, and `checks.cross_artifact_binding.status=passed`. `not_run`, `blocked`, and `unsupported` remain explicit if the signed aggregate contains those states. The verifier is portable across Linux, macOS, and Windows because it uses only Python standard-library file and archive operations. The platform wrappers select Python only and preserve the same JSON stdout and exit-code contract:

| Platform | Wrapper | Success | Blocked/non-passed |
|---|---|---:|---:|
| Linux/macOS | `scripts/verify_operator_artifacts.sh` | `0` | `2` |
| Windows PowerShell | `scripts/verify_operator_artifacts.ps1` | `0` | `2` |
| Direct Python | `scripts/verify_operator_artifact_set.py --require-signed-result` | `0` | `2` |

The wrappers do not alter paths, invoke shells on artifact content, or add platform-specific claims. They enable strict full-chain mode by default, requiring `verification-result.json`. A subprocess caller can parse stdout as one JSON object; stderr remains available for runtime diagnostics. This is wrapper parity evidence, not native packaging evidence.

Direct Python invocation without `--require-signed-result` remains available only for backward-compatible verification of older artifact sets. New transfers should use strict mode.

## Signed verification result

Use `--signed-output` when the offline verification result must enter a later evidence chain:

```sh
./scripts/verify_operator_artifacts.sh \
  --root reports/evidence-pipeline \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --signed-output reports/evidence-pipeline/verification-result.json
```

The output schema is `noesis.signed-operator-artifact-verification.v1`. It binds the verified inventory digest, check projections, verification status, deterministic result digest, and HMAC-SHA256 signature. The signed result has `automatic_execution=false`, `external_execution_claim=false`, and claim boundary `offline_artifact_verification_only`. It proves integrity of the transferred artifact set only; it is not evidence that an external lane executed.

When `verification-result.json` is present under the artifact root, the verifier automatically checks its HMAC and requires its `inventory_digest` to equal the locally verified manifest digest. A signed-result digest mismatch, wrong key, verification-status drift, or inventory binding mismatch returns `blocked` with exit code `2`. Older artifact sets without this file remain backward-compatible and are verified without the optional signed-result check.

When `release-gate.json` is present, strict verification also validates its digest and checks that its post-transfer and release-readiness stage statuses agree with the locally verified chain. A missing optional gate artifact remains compatible with older transfers; a present but tampered or inconsistent artifact is blocked.
