# Bounded AgentLoop Conformance

`noesis_harness.agent_loop.AgentLoop` реализует local cycle observe → pack → lease → act → judge → writeback. Action callback передаётся извне; core loop не вызывает LLM, provider, network или external harness.

| Stop condition | Result | Значение безопасности |
|---|---|---|
| Passing action сообщает `done` | `done` | Lease освобождается после validated completion. |
| Достигнут maximum turn count | `max_turns` | Loop bounded и не может выполняться бесконечно. |
| Lease недоступен | `blocked` | Action callback не вызывается без ownership. |
| Loop guard блокирует повтор | `loop` | Повторяющийся action fingerprint останавливает цикл до action. |
| Context pack failure | `context_over` | Цикл останавливается вместо превышения budget. |
| Judge failure | `judge_fail` | Failed output не считается успешной работой. |
| Action exception | `act_error` | Exception ограничивается result, lease освобождается. |
| Judge exception | `judge_error` | Exception ограничивается result, lease освобождается. |
| Memory write exception | `memory_error` | Failed writeback ограничивается result, lease освобождается. |
| Budget exception | `budget_error` | Budget failure ограничивается result, lease освобождается. |
| Budget exhausted | `budget` | Следующие turns запрещены после исчерпания bounded budget. |

Loop может сохранять memory только после получения action result; promotion остаётся под human approval и отдельными evidence contracts. Это local control-plane loop, а не доказательство autonomous external Hermes execution или self-learning без approval.

Каждый early stop после acquire освобождает lease, включая context-pack failure, loop-guard rejection, action exception, judge exception, memory write exception и budget exception.
 Turn timestamps используют injectable clock, поэтому evidence tests остаются deterministic. Текущие conformance tests покрывают bounded turns, lease-miss action suppression, loop-guard stop, cleanup при failures, exception containment, deterministic timestamps и judge-gated completion. External provider lanes остаются disabled, пока operator не предоставит pinned environments и signed receipts.
