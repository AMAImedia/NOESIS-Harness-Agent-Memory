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
