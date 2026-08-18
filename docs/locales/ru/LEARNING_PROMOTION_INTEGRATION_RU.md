# Learning Promotion Integration Contract

Это supplemental localization English primary contract, связывающий terminal task outcomes с human-governed learning promotion pipeline без automatic skill activation.

| Поверхность | Контракт |
|---|---|
| Task completion | Только terminal states (`done`, `completed`, `success`, `failed`) создают experience receipt; active и неизвестные tasks отклоняются. |
| Evaluator registry | Версии evaluator регистрируются явно и уникально; unknown/duplicate versions fail closed. Evaluator только создаёт deterministic holdout cases и ничего не продвигает автоматически. |
| Promotion operations | Capture, evaluate, propose, approve, promote и rollback выполняются явными вызовами. Task completion не запускает background promotion. |
| Operator telemetry | Lifecycle events bounded и redacted; публикуются в optional `learning_promotion` section read-only HealthServer telemetry и существующего SSE snapshot. |
| Activation | Integration default — `activate=False`; active skill pointer не создаётся task completion или evaluation. |

Events: `experience_captured`, `holdout_evaluated`, `promotion_proposed`, `promotion_approved`, `promotion_completed`, `promotion_rolled_back`. Telemetry содержит только identifiers, states, counts и digests; content-like fields, credentials и API keys recursively redacted.

Этот слой не запускает skill content, не выбирает evaluator implicit, не активирует skill автоматически и не делает claim полной capability обучения. Runtime activation остаётся отдельным capability-gated этапом.

English primary: [`LEARNING_PROMOTION_INTEGRATION.md`](../../LEARNING_PROMOTION_INTEGRATION.md).
