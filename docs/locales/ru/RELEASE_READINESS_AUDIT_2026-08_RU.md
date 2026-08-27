# NOESIS release-readiness аудит

Дата: 2026-08-17

## Решение

**Статус: verification-ready для продолжения private-разработки; ещё не одобрен для публичного релиза.** Pinned coding adapter и cross-agent leakage corpus реализованы и протестированы. Репозиторий остаётся private. Dynamic coding-task execution и hardened OS-level isolation явно помечены `unavailable`, поэтому этот аудит не превращает static verification в заявление о sandbox.

## Верифицированные проверки

| Проверка | Результат | Интерпретация |
|---|---:|---|
| Полная Python-регрессия | **118/118 passed in 3.097 s** | Регрессии после новых слоёв не обнаружено |
| Тесты pinned coding adapter | **4/4 passed** | Покрыты три фиксированные задачи и пути fail-soft |
| Число pinned coding-задач | **3** | Ревизии прикреплены к `2026-08-17.1` |
| Pass rate static coding, n=100 | **1.000000** | Валидные submission'ы проходят детерминированные AST-проверки |
| Среднее/макс static verification | **0.279640 / 0.430400 ms** | Только локальное измерение |
| Статус dynamic execution | **unavailable** | Ненадёжный источник не исполняется |
| Cross-agent leakage кейсы | **8** | Tenant, recipient, private-scope и proposal boundaries |
| Pass rate isolation corpus, n=100 | **1.000000** | Все фиксированные ожидаемые allow/deny-кейсы пройдены |
| Среднее/макс isolation suite | **62.058280 / 110.673900 ms** | Включает setup свежего SQLite broker |
| Сканирование secret-pattern | **clean** | В отслеживаемом тексте проекта нет credential-токенов или приватных ключей |
| Сканирование реальных Python `eval`/`exec` вызовов | **clean** | Строки корпуса, упоминающие запрещённый паттерн, — это тестовые данные, а не вызовы |
| GitHub-репозиторий | **private** | `AMAImedia/NOESIS-Harness-Agent-Memory` |

## Pinned coding adapter

Adapter определяет три фиксированные задачи: `normalize-words-v1`, `safe-join-v1` и `canonical-json-v1`, все на ревизии `2026-08-17.1`. Верификация парсит источник через Python AST и проверяет обязательные имена функций, обязательные вызовы, обязательные ключевые слова и запрещённые вызовы. Адаптер записывает SHA-256 artifact digest и возвращает `failed` для static-нарушений или `unavailable` для неизвестных задач и dynamic execution. Он никогда не вызывает `eval`, `exec`, `compile` или subprocess.

Это воспроизводимый gate для coding-задач, а не покрытие SWE-bench и не execution sandbox. Последующий adapter может добавить user-supplied isolated runner, но этот runner должен быть отдельно аудирован и должен сохранять результат `unavailable`, когда hardening отсутствует.

## Cross-agent leakage corpus

Корпус покрывает: доставку сообщений в рамках одного tenant, запрет cross-tenant сообщений, receive только recipient-ом, запрет записи в private-scope, явное shared-scope предложение, запрет решения с неверным recipient, запрет при unknown sender и запись в собственный private-scope того же агента. Suite тестирует существующую границу `IsolationBroker` и не заявляет process- или memory-изоляцию за пределами этого broker.

Suite намеренно трактует явные предложения иначе, чем неявное разделение памяти. Сообщения recipient-scoped, cross-tenant отправки запрещены, в private scopes другой агент писать не может, и только recipient предложения может решать pending-предложение.

## Release blockers и следующие gates

| Gate | Статус | Требуемое следующее действие |
|---|---|---|
| Публичная видимость | **Blocked by policy** | Сохранять репозиторий private, пока владелец явно не одобрит публичный релиз |
| Dynamic coding execution | **Unavailable** | Добавить и независимо аудировать внешний hardened runner, если требуется |
| Заявление об OS-level sandbox | **Unavailable** | Не заявлять без реального hardened sandbox |
| Branch protection | **Not enabled** | Включить после подтверждения желаемых required checks и policy review |
| Расширенный coding-бенчмарк | **Not yet implemented** | Добавить pinned task expansion только после стабилизации three-task adapter |
| Long-horizon сравнение моделей | **Not yet implemented** | Запускать повторные rollouts с фиксированными model/tools/budget; не выводить по microbenchmarks |

## Команды воспроизведения

```text
python -m unittest discover -s tests -v
python benchmarks/coding_isolation_bench.py --n 100
```

Текущий аудит — это локальный/private engineering gate. Он сообщает измеренные факты и явные unavailable capabilities; он не сертифицирует продакшен-безопасность, качество сторонних моделей или готовность к публичному релизу.