# Bounded AgentLoop Conformance

`noesis_harness.agent_loop.AgentLoop` реализует local cycle observe → pack → lease → act → judge → writeback. Action callback передаётся извне; core loop не вызывает LLM, provider, network или external harness.

| Stop condition | Result | Значение безопасности |
|---|---|---|
| Passing action сообщает `done` | `done` | Lease освобождается после validated completion. |
| Достигнут maximum turn count | `max_turns` | Loop bounded и не может выполняться бесконечно. |
| Lease недоступен | `blocked` | Action callback не вызывается без ownership. |
| Malformed lease response | `lease_shape_error` | Invalid ownership response останавливает цикл до action. |
| Loop guard блокирует повтор | `loop` | Повторяющийся action fingerprint останавливает цикл до action. |
| Context pack failure | `context_over` | Цикл останавливается вместо превышения budget. |
| Pack exception | `pack_error` | Dependency failure ограничивается result, lease освобождается. |
| Malformed pack response | `pack_shape_error` | Invalid pack response отклоняется, lease освобождается. |
| Guard exception | `guard_error` | Dependency failure ограничивается result, lease освобождается. |
| Malformed guard response | `guard_shape_error` | Invalid guard response отклоняется, lease освобождается. |
| Malformed action result | `result_shape_error` | Non-mapping output отклоняется до judge или writeback. |
| Judge failure | `judge_fail` | Failed output не считается успешной работой. |
| Action exception | `act_error` | Exception ограничивается result, lease освобождается. |
| Judge exception | `judge_error` | Exception ограничивается result, lease освобождается. |
| Malformed judge result | `judge_shape_error` | Non-mapping verdict отклоняется, lease освобождается. |
| Memory write exception | `memory_error` | Failed writeback ограничивается result, lease освобождается. |
| Budget exception | `budget_error` | Budget failure ограничивается result, lease освобождается. |
| Malformed budget response | `budget_shape_error` | Invalid budget response отклоняется, lease освобождается. |
| Clock exception | `clock_error` | Timestamp failure ограничивается result, lease освобождается. |
| Lease renewal exception | `lease_renew_error` | Renewal failure ограничивается result, lease освобождается. |
| Budget exhausted | `budget` | Следующие turns запрещены после исчерпания bounded budget. |

Constructor отклоняет неположительный или нецелый `max_turns` и non-callable injected clock до получения любого lease. Action и judge outputs должны быть mappings; malformed outputs ограничиваются как failures. Budget authorization выполняется до memory writeback. Memory writeback выполняется только при `pass=true` от judge и принятом turn budget; rejected или budget-denied candidates не сохраняются.
 Telemetry append failures изолируются и не превращают valid control result в execution failure.
 Loop может сохранять memory только после получения action result; promotion остаётся под human approval и отдельными evidence contracts.
 Это local control-plane loop, а не доказательство autonomous external Hermes execution или self-learning без approval.

LoopGuard отклоняет invalid non-positive bounds до execution и canonicalizes mapping actions перед fingerprinting, поэтому key order не меняет repeat detection. Каждый early stop после acquire освобождает lease, включая context-pack failure, pack exception, loop-guard rejection, guard exception, action exception, judge exception, memory write exception, budget exception и lease renewal exception.
 Turn timestamps используют injectable clock, поэтому evidence tests остаются deterministic. Текущие conformance tests покрывают bounded turns, lease-miss action suppression, loop-guard stop, cleanup при failures, exception containment, deterministic timestamps и judge-gated completion. External provider lanes остаются disabled, пока operator не предоставит pinned environments и signed receipts.
