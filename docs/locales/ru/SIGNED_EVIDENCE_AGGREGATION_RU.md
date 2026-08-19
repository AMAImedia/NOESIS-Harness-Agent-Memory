# Контракт агрегации signed evidence

## Назначение

Aggregator объединяет уже созданные delegated и child-runtime evidence без запуска provider, child process или external lane. Он не позволяет смешивать доказательства разных sessions, tasks, request identities или lanes в одно более сильное утверждение.

## Обязательная binding identity

Каждая запись должна содержать `evidence_id`, `lane`, `session_id`, `task_id`, `request_digest`, `status`, signed `receipt` и signature. Receipt обязан повторять session, task, request digest и иметь `status=passed`. HMAC signature проверяется до включения записи в aggregate digest.

| Условие | Результат aggregation |
|---|---|
| Нет records | `not_run`; execution claim отсутствует. |
| Отсутствует required lane | `not_run`; execution claim отсутствует. |
| Неверная signature или receipt identity mismatch | `blocked`; claim отсутствует. |
| Duplicate evidence ID | `blocked`; claim отсутствует. |
| Non-passed receipt | `blocked`; claim отсутствует. |
| Все required signed records корректны | `passed` только для проверки evidence. `comparative_claim=false`. |

По умолчанию требуются lanes `delegated` и `child_runtime`. Aggregate digest детерминирован по нормализованным records и required lane identities. Verified local aggregate не создаёт Hermes, OpenCode, DeepSeek Harness, native Windows/macOS или worldwide-superiority claim.

> Aggregation подтверждает, что конкретные receipts взаимно связаны и не изменены; она не запускает unrun lane и не превращает local evidence в external comparative evidence.
