# Cross-Platform Release Gate Matrix

`scripts/build_cross_platform_gate_matrix.py` объединяет local native-evidence report и external readiness report в `noesis.cross-platform-release-gates.v1`.

| Lane | Текущий статус | Значение |
|---|---|---|
| Linux local verifier | `passed` | Bounded local evidence lanes прошли. |
| Windows native | `not_run` | Matching Windows host и Python 3.14 недоступны. |
| macOS native | `not_run` | Matching macOS host и Python 3.14 недоступны. |
| Hermes external | `not_run` | Exact immutable revision не pinned. |
| OpenCode external | `not_run` | Exact immutable revision не pinned. |
| DeepSeek Harness external | `not_run` | Exact immutable revision не pinned. |

Aggregate status сейчас `not_run`, `comparative_ready=false`, `native_or_external_execution_claim=false`. Invalid lane status values обрабатываются fail-closed и дают `blocked` с именем lane в `invalid_status_lanes`.

`passed` у local verifier не создаёт native Windows/macOS evidence, external execution evidence или agent-quality ranking. Machine-readable snapshot: [`CROSS_PLATFORM_RELEASE_GATE_MATRIX.json`](../../CROSS_PLATFORM_RELEASE_GATE_MATRIX.json).

Нормативная English-версия: [`CROSS_PLATFORM_RELEASE_GATES.md`](../../CROSS_PLATFORM_RELEASE_GATES.md).
