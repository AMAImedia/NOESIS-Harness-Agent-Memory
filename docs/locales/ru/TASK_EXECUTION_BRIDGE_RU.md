# NOESIS Task Execution Bridge

## Граница ответственности

`TaskExecutionBridge` связывает versioned task/session ledger с безопасными bounded parallel lanes. Он не является model runner и не исполняет model-generated code, shell, tools или executable skills. Callback передаётся владельцем системы; executable work должен отдельно пройти Trust Plane и ChildExecutionRuntime.

## Lifecycle

```text
task.create
  -> task.transition(planned)
  -> task.request_execution
  -> waiting_approval
  -> explicit approval
  -> Actions claim
  -> SafeParallelExecutor lane
  -> Actions complete/requeue
  -> task review или failed
  -> metadata-only stream events
```

`task.request_execution` не запускает работу. Если approval отсутствует, bridge отклоняет запрос до запуска любой lane. Каждая task обязана принадлежать указанной session и иметь stable action ID, совпадающий с `task_id`.

## Security invariants

| Invariant | Проверка |
|---|---|
| Session ownership | Task session ID обязан совпасть с execution session |
| Approval | `approval=True` обязателен; иначе callback не вызывается |
| Action ownership | Actions claim выполняется до callback; foreign active action получает `blocked` |
| Workspace separation | SafeParallelExecutor создаёт уникальную workspace на agent |
| Capability scope | Allowlist/denylist проверяется до thread start |
| Failure recovery | Callback exception → Action `pending`, task `failed` |
| Success boundary | Callback success → Action `done`, task `review` |
| Event safety | SSE sink получает только session/task/agent/kind/state/error metadata; raw output и workspace contents не публикуются |
| Tool boundary | Bridge не вызывает subprocess и не обходит ChildExecutionRuntime |

## Event mapping

`lane_started`, `lane_claimed`, `lane_blocked`, `lane_failed`, `lane_completed`, `task_review_ready` и `task_failed` публикуются через injected event sink. В HTTP integration sink может направлять эти records в `SessionEventBuffer`; sequence/reconnect semantics остаются общим `noesis.session-stream.v1` contract.

## Проверенный результат

Focused bridge/parallel/coordination/command suite: **30/30 passed**. Полный Python 3.14.7 suite: **329/329 passed**, `ResourceWarning: 0`, `git diff --check` passed.
