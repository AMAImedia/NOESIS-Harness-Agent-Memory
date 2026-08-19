# Operator Import Validation

` scripts/validate_operator_import.py` validates a readiness-only operator bundle before importing signed lane and case evidence. It does not execute providers, consume approvals or convert `not_run` into a result.

The validator recomputes the bundle digest, binds the bundle to the exact manifest digest and case IDs, verifies the required lane set, checks lane revisions and protocol fingerprint drift, and then delegates signed evidence and case validation to the comparative report builder. Any bundle, manifest or lane drift produces `status=blocked` and no report score.

| Import status | Meaning |
|---|---|
| `blocked` | Bundle or evidence identity is inconsistent, tampered, unsafe or malformed. |
| `accepted_not_run` | Bundle is consistent, but external evidence is incomplete or lanes remain not_run. |
| `accepted` | Signed evidence and complete case corpus were accepted by the report builder. This still does not set `score_claim=true`. |

The output always includes `external_execution_claim=false` and `score_claim=false`. A valid import is evidence ingestion, not a comparative superiority claim. Provider execution remains outside this command and requires a separate explicit operator action on a matching pinned environment.

*Primary language: English.*
