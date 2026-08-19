# Verification receipts lifecycle ingestion

`verify_ingestion_receipt()` проверяет один signed `noesis.lifecycle-audit-ingestion-receipt.v1`. Проверяются schema, HMAC signature, record identity, bundle digest, audit digest, допустимые action/state и claim-conservative flags.

`verify_ingestion_receipt_audit()` проверяет последовательность receipts до audit-only включения в operator report. Missing input даёт `not_run`; signature или identity failures дают `blocked`; duplicate action IDs, неправильный порядок actions и claim escalation отклоняются. Даже valid result остаётся `claim=false`, `execution_claim=false` и `comparative_claim=false`; receipt verification не закрывает delegated, child-runtime, native, external или comparative lanes.
