# Gate 3 Artifact-Diff Receipts

This is the normative contract for child-runtime execution assurance. Every receipted child run binds its request and policy digests to a canonical before/after artifact manifest, a deterministic artifact diff, and a signed execution receipt.

## Receipt binding

The child runtime captures a path-relative manifest before launching the child and another after the child exits. Each file entry contains a relative path, byte size, and SHA-256 content digest. The diff records added, removed, and changed paths, plus the canonical digest of the complete before/after payload. The receipt stores that diff digest and signs the complete receipt digest with HMAC-SHA256.

| Boundary | Required behavior |
|---|---|
| Canonical paths | Manifest paths are relative to the declared workspace and sorted before hashing. |
| Content integrity | File size and SHA-256 digest are recorded; missing workspace is rejected. |
| Receipt binding | `artifact_diff_digest` is part of the receipt's signed stable payload. |
| Tamper handling | Any modified receipt field, signature, or stored payload fails verification. |
| Replay handling | Existing request identity and recovery receipt checks remain fail-closed. |
| Recovery honesty | A recovery record does not claim rollback or artifact restoration unless the injected handler confirms it. |

## Scope and limitations

The artifact diff proves what the configured workspace changed; it does not itself prove operating-system isolation, network isolation, or semantic safety of generated content. Child execution remains bounded by the Gatekeeper, capability manifest, sandbox backend, output/time budgets, and recovery contracts. Native Windows/macOS execution and external harness A/B remain `not_run` until matching hosts, exact revisions, disposable environments, and signed operator-approved evidence are available.

## Implementation and evidence

The implementation is [`noesis_harness/execution_assurance.py`](../noesis_harness/execution_assurance.py) and its runtime integration is [`noesis_harness/child_execution.py`](../noesis_harness/child_execution.py). Focused coverage is in [`tests/test_execution_assurance.py`](../tests/test_execution_assurance.py), [`tests/test_child_execution.py`](../tests/test_child_execution.py), [`tests/test_execution_recovery.py`](../tests/test_execution_recovery.py), and [`tests/test_chaos_recovery.py`](../tests/test_chaos_recovery.py). The evidence is bounded local execution evidence only.
