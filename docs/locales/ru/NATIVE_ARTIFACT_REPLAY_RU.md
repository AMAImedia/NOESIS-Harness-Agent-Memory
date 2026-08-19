# Контракт replay-проверки нативных артефактов

## Назначение

Контракт проверяет подготовленные оператором артефакты parity для Windows и macOS без запуска непроверенного нативного бинарного файла. Это граница доказательств, а не замена выполнению на соответствующем хосте.

## Статусы

| Статус | Значение | Допустимое утверждение |
|---|---|---|
| `passed` | Совпадающие host/Python identity и обязательные артефакты прошли проверку. | Только статическая проверка replay-артефактов; verifier сам native execution не выполняет. |
| `not_run` | Текущий хост или версия Python не подходят для целевого native lane. | Никакого native claim. |
| `blocked` | Подходящий хост есть, но доказательства отсутствуют, повреждены, устарели или нарушают integrity/security guard. | Никакого native claim. |

## Инварианты

Требуются `environment.json`, `parity-results.json`, `sha256sums.txt` и `sbom.json`. Среда должна запрещать сеть и доступ к credentials. Parity receipt должен явно иметь статус `passed` и операторское execution claim. SHA-256 manifest обязан совпадать с файлами среды и результата, а SBOM обязан перечислять обязательные файлы доказательств.

Replay wrapper не запускает provider, child process, native executable, сетевую операцию или external lane. `artifact_replay_allowed=true` означает только успешную статическую проверку имеющихся доказательств на matching host. Это не создаёт native execution receipt и comparative external score.

## Граница утверждений

Статические manifests, созданные в Linux, и локальные simulations являются только подготовительными доказательствами. Windows/macOS parity может стать `passed` только после запуска операторского bundle на соответствующем matching host и импорта корректного signed receipt через fail-closed ingestion lifecycle.
