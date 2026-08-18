# Learning Promotion Integration Contract

Это supplemental localization English primary contract, связывающий terminal task outcomes из durable task/session event stream с human-governed learning promotion pipeline без automatic skill activation.

| Поверхность | Контракт |
|---|---|
| Durable event stream | `PromotionEventBridge` replay-ит append-only `task_state_changed`; только `committed` и `failed` допускаются к capture, а `cancelled` явно отклоняется. |
| Terminal mapping | `committed` становится успешным promotion outcome, `failed` — failure outcome; active/review/planned/unknown states bridge игнорирует. |
| Policy simulation | `RuntimePolicySimulator` — runtime-owned deterministic policy decision provider без side effects; он возвращает `PolicySimulation` с source/policy digests, agent identity и scope. Missing fields, malformed response и exceptions fail closed. |
| Durable checkpoints | Пишутся `started`, `completed`, `denied` checkpoint events по source task event ID; completed/denied не replay-ятся. Existing receipt переиспользуется по experience ID. |
| Evaluator registry | Версии evaluator регистрируются явно и уникально; unknown/duplicate versions fail closed. Evaluator создаёт deterministic holdout cases, но ничего не продвигает автоматически. |
| Promotion operations | Capture, evaluate, propose, approve, promote и rollback выполняются явными вызовами. Единственная lifecycle entry point — `TaskExecutionBridge.poll_promotion_events(operator_trigger=True)`; `execute()` не poll-ит и не promote-ит implicit. |
| Operator telemetry | Lifecycle и denial events bounded/redacted; публикуются в optional `learning_promotion` section read-only HealthServer telemetry и SSE snapshot. |
| Activation | Integration default — `activate=False`; task completion, policy simulation и evaluation не создают active skill pointer. |

Events: `experience_captured`, `holdout_evaluated`, `promotion_proposed`, `promotion_approved`, `promotion_completed`, `promotion_rolled_back`, `promotion_blocked`. Telemetry содержит identifiers, states, counts, digests и bounded denial reasons; content-like fields, credentials и API keys recursively redacted.

Bridge replay-safe для повторного poll и нового bridge с тем же checkpoint path. `completed`/`denied` source events пропускаются; незавершённый `started` может быть повторно обработан, а receipt lookup предотвращает duplicate capture после сбоя. Approval и activation никогда не выводятся из checkpoint.

Этот слой не запускает skill content, не выбирает evaluator implicit, не активирует skill автоматически и не делает claim полной autonomous learning capability. Runtime activation остаётся отдельным capability-gated этапом.

Implementation: `noesis_harness/promotion_integration.py`; lifecycle wiring: `noesis_harness/execution_bridge.py`; tests: `tests/test_promotion_integration.py` и `tests/test_execution_bridge.py`.

English primary: [`LEARNING_PROMOTION_INTEGRATION.md`](../../LEARNING_PROMOTION_INTEGRATION.md).
