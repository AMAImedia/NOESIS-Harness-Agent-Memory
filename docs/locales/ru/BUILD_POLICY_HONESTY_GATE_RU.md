# Build Policy Honesty Gate

Bounded build-policy runner проверяет packaging и signing policy без выполнения native Windows/macOS build.

| Lane | Результат | Граница |
|---|---|---|
| Windows dry-run | `passed` | Command проверена, но не запущена на Linux host. |
| macOS dry-run | `passed` | Command проверена, но не запущена на Linux host. |
| Signing policy | `passed` | Authenticode и codesign requirements присутствуют; signature не создавалась и не проверялась. |
| Python 3.14 dry-run | `passed` (`3.14.7`) | Проверена identity локального interpreter. |

Machine report: [`PARALLEL_BUILD_POLICY_EVIDENCE.json`](../../PARALLEL_BUILD_POLICY_EVIDENCE.json). Обязательные guards: `native_builds_executed=false`, `network_allowed=false`, `credentials_available=false`, `model_generated_code_executed=false`, а для target dry-runs — `run_permitted=false`.

Dry-run pass проверяет policy и refusal behavior. Он не создаёт Windows `.exe`, macOS `.app`, Authenticode signature, codesign result, notarization result или native execution evidence.

Нормативная English-версия: [`BUILD_POLICY_HONESTY_GATE.md`](../../BUILD_POLICY_HONESTY_GATE.md).
