# Parallel Native Build-Policy Evidence

**Статус:** локально verified  
**Runtime:** CPython 3.14.7 Linux  
**Machine-readable evidence:** `docs/PARALLEL_BUILD_POLICY_EVIDENCE.json`  
**Evidence SHA-256:** `9bbf15a92226c6ee15c53c569afefba7094910362a33d5a250848aa85554f18a`

## Проверенные lanes

| Lane | Проверка | Результат |
|---|---|---|
| `windows-dry-run` | Build command mapping и target verification для Windows | `passed`; `dry_run=true`; `run_permitted=false`; `platform_ok=false`; `python_ok=true` |
| `macos-dry-run` | Build command mapping и target verification для macOS | `passed`; `dry_run=true`; `run_permitted=false`; `platform_ok=false`; `python_ok=true` |
| `signing-policy` | Static Authenticode/codesign/notarization declarations | `passed`; `native_builds_executed=false`; release signatures required |
| `python314-dry-run` | Runtime gate | `passed`; actual `3.14.7` |

## Honesty invariants

На Linux target mismatch блокирует native run **до вызова backend subprocess**. Это проверено unit tests с patched subprocess: `run.assert_not_called()` для Windows и macOS. Static signing policy содержит обязательные release requirements; `--development-unsigned` остаётся только local-only режимом.

Все lanes имеют уникальные workspaces. `network_allowed=false`, `credentials_available=false`, `model_generated_code_executed=false`, `native_builds_executed=false`. Report validator проверяет эти invariants и отсутствие credential-like markers.

## Граница evidence

Эта matrix доказывает корректность dry-run и fail-closed policy. Она не является native build evidence. Реальные `.exe`/`.app`, Authenticode, codesign и notarization появятся только после запуска на соответствующих Windows/macOS hosts.
