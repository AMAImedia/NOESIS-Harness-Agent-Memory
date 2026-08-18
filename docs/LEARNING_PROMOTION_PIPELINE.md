# Human-Governed Learning Promotion Pipeline

This is the normative contract for provenance-bound self-learning promotion. The pipeline is **review-first, approval-required, immutable, rollback-capable, and non-executing**.

## Lifecycle

```text
experience receipt -> deterministic holdout evaluation -> review proposal
        -> explicit approval -> immutable version promotion
        -> verification receipt -> optional activation -> rollback
```

| State | Meaning | Allowed transition |
|---|---|---|
| `review` | Proposal exists and passed deterministic holdout acceptance. | `approved` or `rejected` |
| `approved` | Explicit operator approval and approval tests passed. | `promoted` or `blocked` |
| `promoted` | Immutable version written and verification callback passed. | `rolled_back` |
| `rolled_back` | Active pointer removed or restored to the previous version. | Terminal for that proposal |
| `blocked` | Holdout, leakage, digest, approval, or verification gate failed. | Terminal for that proposal |
| `rejected` | Explicit operator rejection. | Terminal for that proposal |

## Fail-closed acceptance rules

A receipt must bind an experience ID, agent ID, scope, source digest, policy digest, outcome, payload digest, timestamp, and schema version. A holdout evaluation is accepted only when it contains at least one case, every case passes, and no case is marked leaked. Cases are normalized and sorted by `case_id` before hashing, making the evaluation digest deterministic.

A proposal is review-only until explicit approval. Approval requires an operator identity and a passing caller-supplied test hook. Promotion rejects content digest mismatch, missing approval, failed verification, duplicate version directory creation, and any exception raised by the verification callback. The module writes no executable entrypoint and never invokes skill content.

Activation is represented only by an `ACTIVE` pointer to an immutable version. Rollback removes that pointer or restores the previous pointer. A promotion receipt is HMAC-SHA256 signed over the proposal ID, skill name, immutable version, and activation flag. Signature verification uses constant-time comparison.

> Local promotion evidence proves lifecycle integrity only. It does not prove that a promoted skill is generally capable, safe against all prompt injection, or superior to another agent. Those claims require holdout design, independent review, and external benchmark evidence.

## Implementation

The stdlib-only implementation is `noesis_harness/learning_promotion.py`, exported through the package API. Its executable-skill boundary remains disabled by design. Integration with a runtime must preserve capability gates, scope checks, secret scanning, cross-agent leakage holdouts, and explicit operator approval.
