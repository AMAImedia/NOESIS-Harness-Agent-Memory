# Multi-Agent Delegation

This is the normative contract for bounded local delegation. Delegation is **capability-scoped, lease-compatible, workspace-isolated, review-only, and signed**.

## Request and capability gate

A request binds `delegation_id`, `session_id`, `task_id`, `agent_id`, and an explicit capability tuple. Unknown capabilities are denied. Capabilities that can mutate a workspace require both an approval flag and an approval recorded on the request. The delegated callback receives only its lane context; it does not receive another agent's context, workspace, credentials, or parent filesystem path.

| Boundary | Required behavior |
|---|---|
| Capability scope | Reject unknown capabilities before execution. |
| Approval | Reject approval-required capabilities without explicit operator approval. |
| Workspace | Allocate a unique child workspace below the coordinator root and prevent traversal through the lane context. |
| Lease and budget | Pass optional lease, action, cancellation, and duration controls to the bounded executor. |
| Artifact review | Return a review-only artifact manifest and never auto-merge or activate generated content. |
| Evidence | Sign the canonical receipt with HMAC-SHA256 and verify with constant-time comparison. |

## Receipt

A receipt binds the delegation identity, normalized capabilities, workspace, terminal status, artifact digest, output digest, schema version, and signature. The artifact digest covers relative file paths, sizes, and SHA-256 content digests. The receipt itself is excluded from that manifest to avoid circularity. A receipt that is modified, replayed under another identity, or verified with another signing key is rejected.

Delegated work is not a claim of OS-level isolation. The callback path is an orchestration boundary for deterministic local fixtures and approved adapters. Native process sandboxing remains governed by the child-runtime and platform conformance contracts.

## Implementation and evidence

The stdlib-only implementation is [`noesis_harness/delegation.py`](../noesis_harness/delegation.py), built over [`noesis_harness/parallel_agent.py`](../noesis_harness/parallel_agent.py). Focused tests are [`tests/test_delegation.py`](../tests/test_delegation.py), including denied capabilities, missing approval, tampered receipts, and isolated artifact workspaces. The current evidence is bounded local Python 3.14 evidence; external Hermes, OpenCode, and DeepSeek Harness execution remains `not_run` unless exact revisions and disposable environments are present.
