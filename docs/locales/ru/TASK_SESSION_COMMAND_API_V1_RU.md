# NOESIS Task/Session Command API v1

## Назначение

Этот contract предоставляет единую versioned границу для Web UI, terminal client и будущих desktop surfaces. Он не запускает модели, shell, tools или executable skills сам по себе. Команды только изменяют durable session/task ledger; execution должен проходить через Trust Plane, Actions, SafeParallelExecutor и ChildExecutionRuntime.

## Command envelope

```json
{
  "schema_version": "noesis.task-session.v1",
  "command_id": "cmd-unique-128-or-fewer",
  "command": "session.create",
  "payload": {}
}
```

`schema_version` обязателен и должен быть `noesis.task-session.v1`. `command_id` обязателен, ограничен 128 символами и используется для idempotent retry. Unknown commands, unsupported versions, non-object payloads и missing identity fields отклоняются.

## Supported commands

| Command | Payload | Result |
|---|---|---|
| `session.create` | `owner`, optional `session_id` | `SessionRecord` |
| `task.create` | `session_id`, `title`, `owner`, optional `parent_task_id`, `task_id` | `TaskRecord` |
| `task.request_execution` | `task_id`, optional `reason` | `TaskRecord` in `waiting_approval` |
| `task.transition` | `task_id`, `target`, optional `reason` | `TaskRecord` |
| `session.message` | `session_id`, `role`, `content` | `event_id`, `session_id` |

Если `session_id` или `task_id` не заданы в create command, они детерминированно выводятся из `command_id`; повторная отправка той же команды не создаёт новый объект.

## Task state machine

Разрешены только следующие transitions:

```text
created -> planned | cancelled
planned -> waiting_approval | executing | cancelled
waiting_approval -> executing | cancelled
executing -> review | failed | cancelled
review -> committed | rolled_back | executing | cancelled
failed -> planned | cancelled
rolled_back -> planned | cancelled
```

Прямой переход `created -> committed`, обход approval/review или переход из terminal state отклоняется fail-closed.

## HTTP routes

При переданном `TaskSessionStore` и только при явном opt-in mutation доступны:

| Method | Route | Назначение |
|---|---|---|
| `POST` | `/api/commands` | Выполнить versioned command envelope |
| `GET` | `/api/tasks/<task_id>` | Прочитать один task record |
| `GET` | `/api/sessions/<session_id>` | Resume session, tasks, messages и event count |
| `GET` | `/api/sessions/<session_id>/events` | Bounded SSE stream с Last-Event-ID reconnect |

Ответ command route — HTTP `202` и UI envelope с `command` и `sequence`. Ошибка contract — `400`; неизвестный task — `404`; server без session store остаётся read-only и возвращает `405`.

## Streaming invariants

Каждый event имеет `noesis.session-stream.v1`, `session_id`, монотонный `sequence`, `kind`, optional `task_id`, timestamp и bounded `data`. Размер event ограничен 64 KiB. Buffer ограничен по числу events, а reconnect использует `Last-Event-ID`; устаревшие события после eviction не восстанавливаются притворно.

Command events публикуются в stream только после успешной durable dispatch. Секретоподобные поля и credential-like text redacted до persistence и до SSE serialization. Stream не выдаёт raw context, credentials или model-generated executable content.

`task.request_execution` только обозначает намерение и переводит task в `waiting_approval`. Реальный запуск выполняется отдельным `TaskExecutionBridge` только после explicit approval и durable Actions claim.

## Security boundary

Loopback является default binding. Non-loopback требует explicit opt-in, LAN warning acknowledgement и bearer authentication. Session mutation требует переданного `TaskSessionStore`; без него server остаётся read-only. Command API не является approval gate: действия с side effects должны пройти отдельный Gatekeeper/Trust Plane approval и child boundary.

## Verified result

Focused command/session/stream/HTTP suite: **16/16 passed** на Python 3.14.7. Full repository suite после добавления execution bridge: **329/329 passed**, `ResourceWarning: 0`, `git diff --check` passed.
