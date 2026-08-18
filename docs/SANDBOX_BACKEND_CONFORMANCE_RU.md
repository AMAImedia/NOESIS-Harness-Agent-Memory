# Sandbox Backend Conformance

NOESIS теперь имеет общий backend contract для isolated child execution. Реальные backends выбираются явно; система не подменяет macOS/Windows доказательства Linux simulation.

| Backend | Host | Локальный статус | Политика |
|---|---|---|---|
| `linux-bubblewrap` | Linux + `bwrap` | Executable conformance на текущем Linux host | `--unshare-all`, explicit `--unshare-net`, read-only runtime mounts, disposable workspace bind, `shell=False` |
| `macos-sandbox-exec` | macOS + `sandbox-exec` | Backend implemented; Linux host reports `not_run` | deny-by-default profile, workspace read/write allowlist, read-only runtime paths, `deny network*` |
| Windows native | Windows matching host | `not_run` in this lane | Requires native Windows process/job/sandbox evidence |

## Common conformance matrix

| Check | Meaning |
|---|---|
| `argv_present` | Explicit argv exists; no command-string shell wrapper |
| `workspace_binding` | Child receives only declared disposable workspace binding |
| `network_policy_declared` | Backend command/profile explicitly declares network isolation |
| `shell_not_selected` | Shell execution is not selected |
| backend availability | Missing tool or wrong OS produces `not_run`, never a false pass |

`ChildExecutionRuntime` accepts an explicit backend and returns `sandboxed: true` only for backend execution. An unavailable backend returns `denied/sandbox_backend_unavailable`; unsupported environment injection is fail-closed. Non-cooperative process termination remains backend-specific and requires matching native host evidence.

Machine-readable evidence: `docs/SANDBOX_BACKEND_CONFORMANCE_EVIDENCE.json`, SHA-256 `8b9e6fa471183a234d82a9b37304b907749293eee8c9fd8bb019699a5e0c37ba`. Current Linux host: Bubblewrap command conformance `passed`; macOS and Windows records are explicitly `not_run`.
