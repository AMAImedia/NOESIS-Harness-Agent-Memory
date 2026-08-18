# Signed Evidence Fail-Closed Gate

## Purpose

External runner evidence is an integrity envelope for an explicitly approved operator workflow. It is not a public-key release signature, vendor attestation, or proof that a third-party system ran unless the record also reports permitted execution on a matching environment.

## Ingestion contract

`ingest_runner_result.py` accepts a result only when all of the following conditions hold:

| Gate | Required condition | Fail-closed result |
|---|---|---|
| Schema | The runner result uses `noesis.external-runner.v1`; the evidence uses `noesis.runner-evidence.v1`. | Reject the envelope |
| Pinned identity | `system`, `revision`, `model_provider`, `task_manifest_sha256`, `protocol_fingerprint`, `workspace`, and `argv` match the pinned spec exactly. | Add an identity/workspace/argv error and reject |
| Environment | The result contains a declared environment and the workspace is disposable, outside access is denied, and credentials are absent. | Reject the envelope |
| Execution state | Status and execution state are consistent; unavailable or denied execution remains `not_run`. | Reject inconsistent states |
| Metrics | Metrics is a non-empty mapping and every metric has an allowed status. | Reject malformed metrics |
| Credential holdout | Recursive credential-like content scanning finds no token, password, secret, bearer, or credential-shaped value. | Reject the envelope |
| Canonical source | `source_result_sha256` is computed from canonical JSON for the complete result. | Reject a missing or malformed digest |
| Environment identity | `environment_digest` is the SHA-256 digest of the canonical declared environment and is included in the signed envelope. | Reject missing or malformed environment identity |
| Receipt identity | `receipt_id` is deterministically derived from lane, revision, protocol fingerprint, source digest, and environment digest. | Reject stale or mismatched receipts |
| Signature | The canonical unsigned evidence envelope is HMAC-SHA256 signed with a runtime key that is never written to the evidence file. | Reject missing, malformed, or mismatched signatures |

An evidence record is accepted only when the validation error set is empty. The `accepted` field must be exactly boolean `true`; an accepted record must contain an empty `errors` list. A record with `accepted=false` is signed as a rejection record for audit purposes, but it is never eligible for comparative evaluation.

## Verification behavior

`verify_evidence()` is deliberately total over hostile input. It returns `False`, without raising, for non-mappings, missing required envelope fields, wrong schema, non-empty errors, non-boolean acceptance, malformed source hashes, malformed metric containers, invalid signature types or prefixes, invalid signing keys, rejected records, and HMAC mismatches. It does not silently repair or coerce an envelope.

| Condition | Result |
|---|---|
| Valid accepted envelope and matching key | `True` |
| Invalid or missing signature | `False` |
| Missing or malformed field | `False` |
| `accepted` is not exactly `true` | `False` |
| Ingestion errors are present | `False` |
| External runner is not started or is denied | Valid signed `not_run`; never a ranking |
| Fixture-only simulated result | Explicitly simulation-only; never native/external evidence |
| Missing pinned lane | `not_run` when no exact revision exists; `blocked` when a pinned revision has no evidence |
| Duplicate lane record | `blocked`; one system may contribute only one accepted record |
| Environment or revision mismatch | `blocked`; no coercion or fallback |
| Protocol fingerprint conflict | `blocked`; comparative readiness is false |
| Unsupported lane | `unsupported`; never converted to a zero score |

## Readiness matrix

`scripts/external_evidence_readiness.py` emits `noesis.external-evidence-readiness.v1`. Each required lane receives exactly one status: `passed`, `not_run`, `blocked`, or `unsupported`. The matrix also records checks, reasons, accepted receipt IDs, protocol conflicts, a deterministic matrix digest, and `comparative_ready`. A readiness `passed` means evidence ingestion and identity checks passed; it does not mean the external system is superior or that the orchestrator itself executed that system.

## Comparative evaluation boundary

Signed evidence authenticates a record under the controlled key. It does not establish that the key holder is an external vendor, that a model or binary is genuine, that a child process was actually isolated, or that a native host was used. Comparative evaluation additionally requires exact immutable revisions, identical task-manifest and protocol fingerprints, at least two accepted executable records, matching environment evidence, disposable workspaces, and explicit operator approval. Missing lanes remain `not_run` or `blocked`; they must never be converted into a pass, failure, zero score, or superiority ranking.

The Russian supplemental localization is available at [`locales/ru/SIGNED_EVIDENCE_FAIL_CLOSED_RU.md`](locales/ru/SIGNED_EVIDENCE_FAIL_CLOSED_RU.md).
