# Deterministic Signed Report Bundle

## Purpose

The report bundle exports three separate evidence domains in one reproducible archive: `local_execution`, `native_parity`, and `external_comparative`. The domains remain separate inside the bundle and are independently digested.

Bundles without lifecycle receipt audit use `noesis.signed-report-bundle.v1` and the original three domains. Bundles with `lifecycle_receipt_audit` use `noesis.signed-report-bundle.v2` and add a fourth, audit-only domain. v1 verification remains supported. ZIP entries have deterministic ordering, fixed timestamps, fixed permissions, canonical JSON and no compression-dependent output. `manifest.json` records each domain digest and a bundle digest. `signature.json` signs the manifest with HMAC-SHA256.

| Domain | Meaning | Claim boundary |
|---|---|---|
| `local_execution` | Local Python/Linux execution evidence. | Does not imply native or external execution. |
| `native_parity` | Windows/macOS artifact or host parity readiness. | Linux dry-run remains `not_run`. |
| `external_comparative` | Pinned Hermes/OpenCode/DeepSeek evidence readiness. | Local export cannot create competitor scores. |
| `lifecycle_receipt_audit` | Verified operator ingestion receipts. | Audit-only; cannot satisfy execution, native, external, or comparative lanes. |

Verification fails closed for malformed ZIPs, unexpected file sets, manifest drift, signature tampering, or domain digest mismatch. Successful verification means only that the exported bundle is intact and reproducible; it does not execute anything and returns `claim=false` with `export_verification_only`. The receipt domain is normalized before signing with `claim=false`, `execution_claim=false`, `comparative_claim=false`, and all execution/native/external lane flags set to false.

## Operator use

```python
from noesis_harness import build_report_bundle, verify_report_bundle

build_report_bundle(
    "reports/noesis-report.zip",
    local_execution=local_status,
    native_parity=native_status,
    external_comparative=external_status,
    signing_key=operator_key,
)
result = verify_report_bundle("reports/noesis-report.zip", operator_key)
```

Signing keys are supplied by the operator and never written into the archive. The export is suitable for durable audit attachment, but it is not an approval, execution receipt, or comparative result by itself.
