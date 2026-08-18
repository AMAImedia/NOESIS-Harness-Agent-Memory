# Signed Evidence Fail-Closed Gate

## Purpose

External runner evidence is an integrity envelope for an explicitly approved operator workflow. It is not a public-key release signature and it is not proof that a third-party system actually ran unless the record also reports a permitted execution and matching environment.

## Acceptance rules

`ingest_runner_result.py` accepts a result only when the result contract, pinned identity, disposable workspace, argv, metrics, credential holdout, and protocol fields validate. It signs the canonical envelope with a runtime HMAC key that is never persisted.

`verify_evidence()` now fails closed for non-mappings, missing envelope fields, non-empty errors, malformed hashes, invalid signatures, invalid keys, non-accepted records, and malformed metric containers. Verification returns `False` rather than raising on hostile input.

| Condition | Result |
|---|---|
| Valid accepted envelope and matching key | `True` |
| Invalid or missing signature | `False` |
| Missing or malformed field | `False` |
| Accepted flag is not exactly `true` | `False` |
| Ingestion errors are present | `False` |
| External runner not started | Valid signed `not_run`, never a ranking |
| Fixture-only simulated result | Explicitly simulation-only; never native/external evidence |

## Verification boundary

Signed evidence authenticates the record under the controlled key. It does not establish that the key holder is an external vendor, that a model is genuine, or that a native host was used. Comparative evaluation additionally requires identical protocol fingerprints, at least two accepted executable records, exact revisions, and explicit operator approval.

The Russian localization is available in [`SIGNED_EVIDENCE_FAIL_CLOSED_RU.md`](SIGNED_EVIDENCE_FAIL_CLOSED_RU.md).
