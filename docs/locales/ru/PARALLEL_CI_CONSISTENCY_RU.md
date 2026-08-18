# Parallel CI / Packaging Runbook Consistency

**Статус:** локально verified  
**Runtime:** CPython 3.14.7 Linux  
**Machine-readable evidence:** `docs/PARALLEL_CI_CONSISTENCY_EVIDENCE.json`  
**Evidence SHA-256:** `884dd1a55ab5deba55174276d83a45c160b822679ec083eff26d44855cb0ebb8`

## Проверенные lanes

| Lane | Проверка | Результат |
|---|---|---|
| `ci-markers` | CI packaging job содержит Python 3.14 verifier, portable builder/verifier и Windows/macOS mismatch gates | `passed`; missing markers: `[]` |
| `runbook-markers` | Native packaging runbook согласован с CI: Python 3.14.7, SHA/SBOM verifier, development-unsigned local-only и native evidence boundary | `passed`; missing markers: `[]` |
| `portable-ci-gate` | Deterministic source-portable fixture проходит build + manifest/SBOM/SHA verification | `passed`; 2 files |
| `target-honesty-gate` | Windows/macOS verifier на Linux не создаёт native evidence | `passed`; оба `not_run`, `target_host_or_python_mismatch` |

## Safety invariants

Все lanes получили уникальные workspaces. `native_builds_executed=false`, `network_allowed=false`, `credentials_available=false`, `model_generated_code_executed=false`. Report validator завершился `PASS`.

CI теперь дополнительно проверяет active Python 3.14 runtime, запускает `verify_portable_artifact.py` после создания portable ZIP и требует fail-closed `target_host_or_python_mismatch` для обоих native targets. Runbook содержит те же команды и явно запрещает использовать `--development-unsigned` как release evidence.

## Boundary

Проверка подтверждает согласованность CI/runbook plumbing и portable artifact gates. Она не является доказательством Windows `.exe`, macOS `.app`, Authenticode, codesign, notarization или external A/B execution. Эти gates требуют соответствующих target hosts и pinned external environments.
