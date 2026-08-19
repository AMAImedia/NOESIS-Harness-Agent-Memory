# Lifecycle Ingestion Receipt Verification

`verify_ingestion_receipt()` verifies one signed `noesis.lifecycle-audit-ingestion-receipt.v1` receipt. It checks schema, HMAC signature, record identity, bundle digest, audit digest, allowed action/state and claim-conservative flags.

`verify_ingestion_receipt_audit()` verifies a receipt sequence before audit-only inclusion in an operator report. It rejects missing input as `not_run`, signature or identity failures as `blocked`, duplicate action IDs, invalid action ordering and claim escalation. A valid result is still `claim=false`, `execution_claim=false`, and `comparative_claim=false`; receipt verification cannot satisfy delegated, child-runtime, native, external or comparative lanes.
