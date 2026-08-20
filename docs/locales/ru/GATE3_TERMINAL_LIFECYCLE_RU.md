# Gate 3 Terminal Lifecycle Assurance — русская локализация

Это supplemental-описание English primary contract для terminalizing child-runtime execution runs в durable recovery ledger. Run может перейти из `running` ровно в один terminal outcome: `completed`, `failed`, `timed_out` или `denied`.

## Idempotent completion

Точное повторение terminal completion является no-op и возвращает существующую durable record. Попытка изменить terminal status, post-run workspace digest или receipt ID отклоняется с `execution_run_terminal_conflict`. Update защищён состоянием `running`, поэтому retry не перезаписывает terminal record после crash или concurrent completion.

| Случай | Результат |
|---|---|
| Первое завершение running run | Записывает terminal state, workspace-after digest, receipt ID и timestamp. |
| Точное повторное завершение | Возвращает существующую terminal record без mutation. |
| Другой terminal payload | Fail-closed с `execution_run_terminal_conflict`. |
| Неизвестный run | Fail-closed с `execution_run_not_found`. |
| Неподдерживаемый terminal status | Fail-closed с `invalid_recovery_terminal_status`. |

Lifecycle guard дополняет signed receipt storage, artifact-diff binding, request identity replay denial, recovery action fingerprints и explicit rollback-handler confirmation. Он не утверждает OS-level isolation или восстановление каждого artifact byte.

English primary contract: [`GATE3_TERMINAL_LIFECYCLE.md`](../../GATE3_TERMINAL_LIFECYCLE.md).
