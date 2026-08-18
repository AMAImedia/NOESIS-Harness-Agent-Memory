# Parallel Native Evidence Matrix

**Статус:** локально verified  
**Runtime:** CPython 3.14.7 Linux  
**Machine-readable evidence:** `docs/PARALLEL_NATIVE_EVIDENCE.json`  
**Evidence SHA-256:** `d48f8807229e9d6c5ffcd872dcecfcf87b56b2b3f6038392a9b46bc31f6f0d79`

## Parallel lanes

| Lane | Проверка | Результат |
|---|---|---|
| `portable-sha-sbom` | Создание deterministic portable fixture и проверка manifest/SBOM/archive SHA-256 coverage | `passed`; 2 payload files; artifact SHA зафиксирован в evidence |
| `static-manifests` | Windows/macOS static manifest schema и release gates | `passed`; `native_builds_executed=false` |
| `python314-identity` | Active runtime identity | `passed`; CPython `3.14.7` |
| `native-target-matrix` | Windows/macOS native artifact verifier on current host | `passed` as honesty check; both target evidences `not_run` because actual platform is Linux |

## Fail-closed results

| Case | Expected | Observed |
|---|---|---|
| Linux pretending to be Windows native host | Must not verify | `not_run`, `target_host_or_python_mismatch` |
| Linux pretending to be macOS native host | Must not verify | `not_run`, `target_host_or_python_mismatch` |
| Portable payload tampering | Must fail SHA-256 gate | Covered by focused test |
| Unexpected ZIP payload | Must fail manifest coverage | Covered by focused test |
| Missing manifest/SBOM | Must fail closed | Covered by focused test |

## Parallel safety

Все четыре lanes получили уникальные workspaces. `network_allowed=false`, `credentials_available=false`, `model_generated_code_executed=false`, `native_builds_executed=false`. Вызовов subprocess, model provider или signing tools в этом Linux run не было.

## Boundary

Эта matrix подтверждает **static packaging/evidence plumbing**, deterministic portable SHA/SBOM verification и честное target mismatch behavior. Она не создаёт доказательств `.exe`/`.app`, Authenticode, codesign, notarization или native target build; такие gates остаются `EXTERNAL HOST REQUIRED`.
