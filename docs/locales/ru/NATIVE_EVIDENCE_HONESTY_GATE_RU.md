# Native Evidence Honesty Gate

Локальный раннер нативных доказательств выполняет четыре ограниченные дорожки без сборки или подписи нативного Windows- или macOS-артефакта.

| Дорожка | Локальный результат | Граница утверждений |
|---|---|---|
| Portable SHA/SBOM | `passed` | Проверяет локальный portable-фикстуру, а не нативный артефакт. |
| Static packaging manifests | `passed` | Проверяет только политику манифеста; нативная сборка не выполнялась. |
| Python 3.14 identity | `passed` (`3.14.7`) | Подтверждает локальный интерпретатор, используемый дорожкой, а не целевую упаковку. |
| Windows target matrix | `passed` как verifier-дорожка; evidence `not_run` | Linux-хост не совпадает; утверждения о Windows `.exe` нет. |
| macOS target matrix | `passed` как verifier-дорожка; evidence `not_run` | Linux-хост не совпадает; утверждения о macOS `.app` нет. |

Машиночитаемый отчёт — [`PARALLEL_NATIVE_EVIDENCE.json`](PARALLEL_NATIVE_EVIDENCE.json). Обязательные guard-поля: `native_builds_executed=false`, `network_allowed=false`, `credentials_available=false`, `model_generated_code_executed=false`.

`passed` verifier-дорожки означает, что правило честности соблюдено. Это НЕ означает, что целевой артефакт был собран, подписан, нотаризован или выполнен на Windows/macOS. Утверждения о нативной сборке требуют совпадающих целевых хостов и окружений Python 3.14.
