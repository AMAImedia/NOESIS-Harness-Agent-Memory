# Pinned External Lane Operator Preflight

`build_operator_preflight()` validates prerequisites for Hermes, OpenCode and DeepSeek Harness without executing any provider or probing an executable by running it. The result is `noesis.external-lane-preflight.v1`.

A lane is `ready` only when an exact revision and an existing pinned executable path are declared. Global readiness additionally requires a workspace, deny-by-default network, absent credentials and a disposable workspace policy. Missing or unsafe prerequisites return `not_run` with bounded check names.

| Field | Required value |
|---|---|
| `execution_allowed` | `false` |
| `automatic_execution` | `false` |
| `operator_approval_required` | `true` |
| `external_execution_claim` | `false` |

`ready_for_operator_approval` means only that the static preflight passed. It does not mean that a lane ran, produced a receipt, or earned a score. Actual execution remains a separate operator-approved pinned-runner operation.
