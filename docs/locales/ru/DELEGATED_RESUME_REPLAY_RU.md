# Контракт resume и replay для delegated tasks

## Назначение

Делегированная child-задача должна переживать прерывание без скрытого повторного запуска старого запроса. Контракт связывает delegation с неизменяемыми session, task, agent, workspace, capabilities и request identity.

| Состояние | Значение | Поведение resume |
|---|---|---|
| `created` / `checkpointed` | Делегация существует и может сохранять checkpoints. | Обычное выполнение идёт в пределах исходной approval boundary. |
| `interrupted` / `failed` | Child остановился до terminal result. | Resume требует нового operator approval для последнего checkpoint. |
| `resume_approved` / `resuming` | Новый approval создан или использован. | Approval одноразовый; request identity должна совпадать точно. |
| `completed` / `cancelled` | Terminal state. | Checkpoint и replay запрещены. |

## Инварианты

Append-only `DelegatedResumeStore` не запускает child process. Он хранит только identity и lifecycle evidence. Resume approval связывается с delegation identity, digest approval token и digest последнего checkpoint. Изменение workspace, capabilities, agent, task, session или другого поля запроса вызывает `delegation_request_mutated` и отклоняется.

После использования approval повторная попытка отклоняется как `resume_approval_replayed`. Если checkpoint изменился после approval, он становится устаревшим и отклоняется как `resume_checkpoint_drift`. Terminal delegation не принимает поздние checkpoints или resume approvals.

> Resume record разрешает одну утверждённую попытку продолжения, но не разрешает повтор произвольной исторической команды.

## Граница доказательств

Store предоставляет durable state и deterministic replay guards для интеграции с `TaskExecutionBridge` и `ChildExecutionRuntime`. `TaskExecutionBridge.resume_delegated()` потребляет одноразовый approval до перевода failed task через `planned` в `waiting_approval`, после чего использует обычные Actions claim, workspace binding, child runtime и receipt verification gates. Отсутствующий или повторный approval останавливает процесс до запуска callback.

Store сам не выдаёт capabilities, не обходит sandbox policy, не запускает providers и не активирует executable skills. Эти действия остаются под контролем Trust Plane, Child Execution Runtime, sandbox backend, Actions claim и operator approval contracts. HealthServer показывает только ограниченный read-only статус resume с `automatic_resume=false`; telemetry не является управляющей командой.
