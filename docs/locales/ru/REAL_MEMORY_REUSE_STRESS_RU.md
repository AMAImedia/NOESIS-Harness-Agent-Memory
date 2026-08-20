# Real Durable Memory Reuse Stress — русская локализация

Это supplemental-описание English primary contract для memory-quality gate, который измеряет durable recall из реального SQLite-backed `Memory` через повторяющиеся sessions и reopen boundaries. Gate является **deterministic, bounded, trace-backed** и честно разделяет fixture evidence и external claims.

## Contract

Stress runner записывает один relevant semantic fact и bounded набор distractors для каждой repetition. Затем он запрашивает реальный memory store, сохраняет selected и relevant IDs в durable quality trace store, закрывает и открывает memory database заново и проверяет, что relevant fact снова recallable. Aggregate report содержит recall distribution, mean, session/case counts, persistence status и SHA-256 distribution digest.

| Требование | Acceptance rule |
|---|---|
| Real storage | Facts записываются через `Memory.save`, а не напрямую в quality records. |
| Real recall | Selection приходит из `Memory.recall`; evaluator не подставляет expected answer. |
| Durable traces | Каждый case сохраняется через `DurableMemoryQualityTraceStore` и загружается для aggregation. |
| Reopen boundary | Memory database открывается заново после каждой repetition. |
| Repeated distribution | Repetitions ограничены `1..100`; scale и token budget должны быть положительными. |
| Determinism | Session IDs, query tokens, case IDs и distribution digest детерминированы для фиксированной формы запуска. |
| Fail-closed | Invalid bounds и trace conflicts отклоняются; missing traces не создают report. |

Gate измеряет только local persistence и retrieval behavior. Он не доказывает general intelligence, semantic coverage или superiority. Native Windows/macOS, external Hermes/OpenCode/DeepSeek Harness A/B и model-based long-context claims остаются `not_run` до matching pinned environments и signed operator-approved evidence.

English primary contract: [`REAL_MEMORY_REUSE_STRESS.md`](../../REAL_MEMORY_REUSE_STRESS.md).
