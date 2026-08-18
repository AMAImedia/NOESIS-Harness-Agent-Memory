# Безопасное parallel multi-agent execution в NOESIS

## Назначение

`SafeParallelExecutor` — это bounded orchestration layer для уже одобренных локальных callbacks. Он не запускает model-generated code, shell commands, tools или executable skills. Любой executable tool/skill обязан пройти отдельный `ChildExecutionRuntime` и его Gatekeeper/approval/security checks.

> Parallel scheduling не является OS sandbox. Он обеспечивает orchestration isolation и fail-closed policy, а не заменяет Bubblewrap, Windows Job Objects/AppContainer или macOS sandbox-exec/seatbelt.

## Инварианты

| Инвариант | Реализация |
|---|---|
| Agent identity | Каждая lane содержит уникальные `agent_id` и `task_id` |
| Session provenance | Callback получает неизменяемые `session_id`, `agent_id`, `task_id` |
| Workspace isolation | Каждая lane получает уникальную child directory под общей root |
| Traversal defense | Relative-only path helper; resolved path обязан оставаться под workspace |
| Symlink defense | Root и каждый path component проверяются на symlink |
| Capability scope | Разрешены только read, workspace_write, memory read/write, signal_send, provenance |
| Hard deny | Credentials, secret_read, cross_agent_read, shared_workspace, inline_code, shell и unbounded_process запрещены |
| Approval | Write/memory/signal capabilities требуют explicit approval |
| Network | Context сообщает `network_allowed=False`; сетевой вызов не предоставляется |
| Credentials | Context сообщает `credentials_available=False`; credential material не передаётся |
| Concurrency | `max_concurrency` ограничен диапазоном 1…8 |
| Failure isolation | Исключение одной lane превращается в failed result и не отменяет независимые lanes |
| Deterministic output | Results сортируются по `task_id`; audit records сохраняют provenance |

## Safe execution pattern

```text
Plan
  -> validate identities/capabilities/workspaces
  -> require explicit approval for mutating scopes
  -> create unique per-agent directories
  -> run bounded callbacks
  -> collect failed/passed results without cross-lane cancellation
  -> hand executable work to ChildExecutionRuntime
  -> persist decision/audit evidence
```

Общий workspace, общий mutable context, скрытые credentials и неограниченное создание processes намеренно не поддерживаются. Межагентное взаимодействие должно проходить через scoped signals или проверенные provenance-bearing records, а не через прямое чтение чужой workspace.

## Проверенный локальный результат

Focused Python 3.14 suite: **8/8 passed** для parallel executor; совместно с coordination tests — **19/19 passed**. Полный repository suite после lease integration: **317/317 passed**, `ResourceWarning: 0`. Проверены bounded concurrency, unique workspaces, provenance identity, capability denial, approval denial, traversal defense, TTL lease blocking/release и fail-isolated callback errors.

Следующий security step — подключить этот orchestrator к durable task/action ledger и recovery coordinator, не разрешая ему обходить Trust Plane или child boundary.


## Durable action recovery

Для action/task ledger добавлен owner-only `Actions.requeue(aid, agent)`. Он возвращает только текущий `active` action его владельцу в `pending`; чужой agent не может перехватить recovery. Это позволяет bounded parallel runner безопасно requeue-ить failed/interrupted work после recovery coordinator, не меняя ownership произвольно.

После lease integration и requeue regression: focused coordination/parallel tests **20/20 passed**; полный suite **318/318 passed**, `ResourceWarning: 0`.


## Durable Actions и RecoveryCoordinator integration

`SafeParallelExecutor` теперь принимает существующий `Actions` store. Для каждой lane lifecycle имеет строгий порядок: `pending → active` через owner claim, callback запускается только после claim, успешный callback переводит action в `done`, а exception возвращает action в `pending` через owner-only `requeue`. Если action уже принадлежит другому agent, callback не запускается.

`RecoveryCoordinator` получил опциональный Actions store и явные `action_id`/`action_owner`. Во время crash recovery он одновременно сохраняет существующий best-state/fiber/work recovery path и пытается вернуть только указанный active action его текущему владельцу. Результат фиксируется в `DurableRecoveryReport.requeued_actions`. Это не заменяет best-state verification и не позволяет recovery-agent переприсвоить чужую работу.

После integration focused suite: **25/25 passed**. Полный Python 3.14.7 suite: **321/321 passed**, `ResourceWarning: 0`, `git diff --check` passed.
