# Multi-Agent Delegation — русская локализация

Это supplemental-описание English primary contract для bounded local delegation. Delegation является **capability-scoped, lease-compatible, workspace-isolated, review-only и signed**.

## Request и capability gate

Request связывает `delegation_id`, `session_id`, `task_id`, `agent_id` и явный capability tuple. Unknown capabilities отклоняются. Capabilities, способные изменять workspace, требуют и approval flag, и approval в request. Callback получает только свой lane context: context другого агента, workspace, credentials и parent filesystem path не передаются.

| Boundary | Требование |
|---|---|
| Capability scope | Unknown capabilities отклоняются до execution. |
| Approval | Approval-required capabilities без explicit operator approval отклоняются. |
| Workspace | Выделяется уникальный child workspace внутри coordinator root; traversal через lane context запрещён. |
| Lease и budget | Optional lease, action, cancellation и duration controls передаются bounded executor. |
| Artifact review | Возвращается review-only artifact manifest; auto-merge и activation отсутствуют. |
| Evidence | Canonical receipt подписывается HMAC-SHA256 и проверяется constant-time comparison. |

Receipt связывает delegation identity, normalized capabilities, workspace, terminal status, artifact digest, output digest, schema version и signature. Receipt исключён из собственного manifest digest, чтобы избежать circularity. Изменённый или replayed receipt fail-closed отклоняется.

Delegated work не является заявлением об OS-level isolation. Native process sandboxing остаётся предметом child-runtime и platform conformance contracts. Текущая evidence bounded local Python 3.14; external Hermes, OpenCode и DeepSeek Harness остаются `not_run` без exact revisions и disposable environments.

English primary contract: [`MULTI_AGENT_DELEGATION.md`](../../MULTI_AGENT_DELEGATION.md).
