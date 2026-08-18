# Cross-Platform Release Gate Matrix

`scripts/build_cross_platform_gate_matrix.py` combines the local native-evidence report and external readiness report into `noesis.cross-platform-release-gates.v1`.

| Lane | Current status | Interpretation |
|---|---|---|
| Linux local verifier | `passed` | Bounded local evidence lanes passed. |
| Windows native | `not_run` | Matching Windows host and Python 3.14 are unavailable. |
| macOS native | `not_run` | Matching macOS host and Python 3.14 are unavailable. |
| Hermes external | `not_run` | Exact immutable revision is not pinned. |
| OpenCode external | `not_run` | Exact immutable revision is not pinned. |
| DeepSeek Harness external | `not_run` | Exact immutable revision is not pinned. |

The aggregate status is currently `not_run`, `comparative_ready=false`, and `native_or_external_execution_claim=false`. Invalid lane status values are fail-closed and produce `blocked` with the lane name in `invalid_status_lanes`.

A local verifier `passed` status does not create native Windows/macOS evidence, external execution evidence, or an agent-quality ranking. The machine-readable snapshot is [`CROSS_PLATFORM_RELEASE_GATE_MATRIX.json`](CROSS_PLATFORM_RELEASE_GATE_MATRIX.json). Operator bundles are documented in [`NATIVE_PARITY_OPERATOR_RUNBOOK.md`](NATIVE_PARITY_OPERATOR_RUNBOOK.md); their target lanes remain `not_run` until matching hosts execute the commands and emit environment and parity artifacts. The preparation API is `noesis_harness.native_parity`.
