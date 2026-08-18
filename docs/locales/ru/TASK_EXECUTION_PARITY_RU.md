# Cross-Platform Task Execution Parity

## Локально доказанный путь

`run_task_execution_parity.py` проверяет один end-to-end local-only сценарий: durable session → task creation → planned → waiting approval → Gatekeeper commit → child process → SafeParallelExecutor → task review → bounded SSE event stream → action requeue recovery.

| Assertion | Local result |
|---|---|
| Child execution | `completed`, direct process-group boundary |
| Approval | Gatekeeper prepare → approve → commit required before child run |
| Task state | `waiting_approval → executing → review` |
| SSE | Monotonic sequences and Last-Event-ID reconnect are bounded and deterministic |
| Recovery | Owned active action returns to `pending` through owner-only requeue |
| Credential/model boundary | No model/provider/network call; no model-generated code in parent |

## Evidence boundary

The machine-readable record is `docs/TASK_EXECUTION_PARITY_EVIDENCE.json` with schema `noesis.task-execution-parity.v1`. It is **local-only evidence**. Linux/Bubblewrap is inventoried but not selected for this smoke because the portable Python executable path is not part of the backend's explicitly mounted runtime roots.

macOS `sandbox-exec`, Windows native process/job termination and external Hermes/OpenCode/DeepSeek Harness lanes remain `not_run` until matching hosts, exact revisions, operator approval and signed evidence are available. These states must not be converted into comparative scores.

## Operator order

Run the local smoke with Python 3.14, then run the same test contract on matching macOS and Windows hosts. For external lanes, pin exact revisions and environment digests before invoking the connector-neutral runner. Ingest only records that pass strict execution/status/hash validation.
