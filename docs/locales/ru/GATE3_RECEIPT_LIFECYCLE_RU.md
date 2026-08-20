# Gate 3 Receipt Lifecycle Transitions — русская локализация

Это supplemental-описание English primary contract для immutable execution receipt lifecycle transitions. Receipt history является append-only: новый receipt может описывать разрешённый transition, но существующий receipt никогда не мутируется.

## Разрешённые transitions

| Previous outcome | Allowed next outcomes |
|---|---|
| `prepared` | `committed`, `rejected`, `failed`, `timed_out` |
| `committed` | `rolled_back` |
| `failed` | `rolled_back` |
| `timed_out` | `rolled_back` |
| `rejected` | None |
| `rolled_back` | None |

Validator также требует одинаковые request digest, policy digest, workspace-before digest и artifact-diff digest. Точно такой же receipt является immutable idempotent no-op. Другой request, policy, workspace, artifact binding или unsupported outcome transition fail-closed отклоняется.

Контракт дополняет durable receipt-store audit, signed receipt verification, artifact-diff binding, terminal recovery lifecycle и explicit rollback-handler confirmation. Он не позволяет использовать valid receipt как evidence для другого request или artifact state.

English primary contract: [`GATE3_RECEIPT_LIFECYCLE.md`](../../GATE3_RECEIPT_LIFECYCLE.md).
