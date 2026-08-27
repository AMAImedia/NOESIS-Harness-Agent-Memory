# Release Audit и граница внешней готовности

Read-only release audit теперь потребляет `docs/EXTERNAL_EVIDENCE_READINESS_MATRIX.json` как guard для утверждений. Перед тем как считать аудит репозитория структурно валидным, он проверяет схему readiness, словарь из четырёх статусов, наличие дорожек и `native_or_external_execution_claim == false`.

Артефакту readiness допустимо оставаться `not_run` для локального/приватного релиз-кандидата. Это ожидаемо, когда точные ревизии Hermes, OpenCode и DeepSeek Harness или подходящие хосты недоступны. Release audit отражает это состояние в `external_readiness` и не преобразует его ни в сравнительный pass, ни в оценку.

| Результат аудита | Интерпретация |
|---|---|
| `external_readiness.errors=[]` и `overall_status=not_run` | Guard доказательств структурно валиден; внешнее исполнение не было продемонстрировано. |
| `external_readiness.errors=[]` и `overall_status=blocked` | Матрица обнаружила конфликт целостности, идентичности, replay, дубликата или протокола. |
| `external_readiness.errors` не пуст | Артефакт readiness невалиден, release audit завершается отказом. |
| `native_or_external_execution_claim=true` | Невалидно для данной локальной границы релиза; release audit завершается отказом. |

Эта интеграция — локальный evidence-plumbing gate. Она не создаёт доказательств нативной Windows/macOS сборки, стороннего исполнения и не формирует сравнительного рейтинга превосходства.
