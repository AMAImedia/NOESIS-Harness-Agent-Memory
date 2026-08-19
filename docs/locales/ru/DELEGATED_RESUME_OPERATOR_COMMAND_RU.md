# Operator-owned команда delegated resume

## Назначение

Команда operator resume является единственным control-plane путём, который может разрешить продолжение delegated task. Telemetry, snapshots и SSE остаются read-only и не могут запускать resume.

## Контракт

Команда использует `noesis.delegated-resume-action.v1` и связывает `action_id`, `operator_id`, `session_id`, `task_id`, `approval_id` и immutable request digest через HMAC-SHA256 signature. Аутентифицированный operator должен совпадать с `operator_id` и иметь scope `task:resume`.

| Guard | Поведение при нарушении |
|---|---|
| Отсутствует handler или operator context | HTTP `405`/`403`; callback не запускается. |
| Неверные schema или signature | Отклонение до callback. |
| Неверный operator или отсутствует `task:resume` | Отклонение до callback. |
| Повторный `action_id` | Возвращается durable `replayed`; callback не повторяется. |
| Устаревший или повторный delegated approval | Его отклоняет `DelegatedResumeStore`. |
| Ошибка callback | Добавляется signed `rejected` receipt; ошибка не превращается в success. |

Authenticated endpoint: `POST /api/delegated-resume`. Он принимает только signed command object и возвращает ограниченное описание action с redacted result metadata. Executor добавляет в append-only audit log receipt `noesis.delegated-resume-receipt.v1`, который связывает action, operator, session, task, status и result digest.

## Граница автоматизации

Команда принадлежит operator, а не autonomous loop. Background process её не опрашивает, telemetry не может её вызвать, а endpoint не создаёт approval IDs самостоятельно. Caller обязан передать свежий approval из delegated resume lifecycle. Actions claim, workspace binding, sandbox, child-runtime и execution-receipt guards остаются обязательными.
