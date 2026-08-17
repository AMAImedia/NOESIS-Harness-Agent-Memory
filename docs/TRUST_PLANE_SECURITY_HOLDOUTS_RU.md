# Trust Plane Security Holdouts

## Phase 5 T-01 — Child execution boundary

Этот документ фиксирует проверяемые security invariants для child runtime. Core control plane не исполняет model-generated code; отдельная process boundary запускает только явно approved и committed request.

| Holdout | Ожидаемое поведение | Фактический статус |
|---|---|---|
| Gatekeeper commit missing | `denied / gatekeeper_commit_required` до запуска | `PASS` |
| Network requested without verified adapter | `denied / network_isolation_unavailable_fail_closed` | `PASS` |
| Inline code flags (`-c`, `--eval`, `--execute`, `-e`) | `denied / inline_code_execution_forbidden` | `PASS` |
| Non-allowlisted executable | `denied / executable_not_allowlisted` | `PASS` |
| Traversal outside workspace | `denied / entrypoint_outside_workspace` | `PASS` |
| Symlink entrypoint | Symlink проверяется до path resolution и отклоняется | `PASS` |
| Unknown environment key | `denied / environment_key_not_allowlisted` | `PASS` |
| Output over budget | Bounded output и `failed / output_budget_exceeded` | `PASS` |
| Credential-like output | Value redacts to `[REDACTED_CREDENTIAL]`, result `failed / credential_like_output_blocked` | `PASS` |
| Timeout | Process termination и `timeout / timeout_budget_exceeded` | `PASS` |

> Этот runtime является process boundary, но не заменяет hardened OS sandbox. Network access остаётся fail-closed, пока отдельный verified sandbox backend не предоставлен. Linux Bubblewrap evidence ведётся отдельно; Windows/macOS native isolation требует target-host evidence.

## Evidence

На Python 3.14.7 focused child-runtime suite: **9/9 passed**. Полный suite: **294/294 passed**. `ResourceWarning`: **0**. Raw credential-like output не сохраняется в `ExecutionResult`; security decision фиксирует только bounded redacted output и reason code.


## Phase 5 T-02 — Context Firewall

| Holdout | Ожидаемое поведение | Фактический статус |
|---|---|---|
| Mixed-scope ordering | Разрешённые элементы сохраняют порядок; заблокированные redacted и не сдвигают provenance | `PASS` |
| Restricted content by default | Без explicit approval restricted/sensitive item не попадает в model context | `PASS` |
| Explicit approval | Approval позволяет включить явно запрошенный item, но решение остаётся отдельным и проверяемым | `PASS` |
| Resource provenance | `included_resource_ids` сохраняются в том же порядке, что и included items | `PASS` |
| Stable redaction digest | Одинаковый разрешённый текст даёт одинаковый `sha256:` digest независимо от повторного вызова | `PASS` |
| Invalid scope configuration | Пустой `allowed_scopes` или item без scope отклоняются fail-closed | `PASS` |
| Context budget | Текст не превышает `max_chars`; overflow item получает `truncated` | `PASS` |

На Python 3.14.7 Context Firewall focused suite: **6/6 passed**. Полный suite после T-02: **297/297 passed**; `ResourceWarning`: **0**. Digest намеренно покрывает assembled text, а provenance IDs доступны отдельным полем и не подменяются текстовой hash-записью.


## Phase 5 T-03 — Resource lineage parent-chain

| Holdout | Ожидаемое поведение | Фактический статус |
|---|---|---|
| Parent identity | `parent_observation` должен существовать в той же session; неизвестный или cross-session parent отклоняется | `PASS` |
| Sensitivity non-downgrade | Derived observation не может объявить меньшую sensitivity, чем parent | `PASS` |
| Cross-agent derivation | Derived resource сохраняет taint для другого agent в той же session | `PASS` |
| Scope-confusion egress | Agent не может вывести derived sensitive/restricted resource без explicit approval | `PASS` |
| Idempotent observation | Повтор одинакового observation не создаёт новую запись и не сохраняет raw content | `PASS` |

Lineage parent references теперь проверяются по event identity; `observations()` возвращает проверяемый `event_id`, а payload не содержит raw content. На Python 3.14.7 focused lineage suite: **5/5 passed**. Полный suite после T-03: **299/299 passed**; `ResourceWarning`: **0**.
