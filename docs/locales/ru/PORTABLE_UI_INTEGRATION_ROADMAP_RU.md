# NOESIS — переносимая control plane

Дата: 2026-08-17

## Решение

NOESIS должен добавить **переносимую, кросс-платформенную control plane** для Windows и macOS, но не должен копировать Hermes Studio, Hermes WebUI или DeepSeek Harness в stdlib-only ядро. Корректный дизайн — это тонкий опциональный UI и адаптер runtime вокруг существующего NOESIS-ядра.

В ходе исследования найдены четыре полезные референсные реализации. Hermes WebUI демонстрирует лёгкий self-hosted браузерный интерфейс с сессиями, workspace, профилями, провайдерами, памятью, skills, cron и аутентификацией, лицензия MIT [1]. DeepSeek Harness демонстрирует plugin/bundle-архитектуру, где адаптеры моделей, инструменты, сессии и агентный цикл заменяемы [2] [3]. DSH Desktop демонстрирует desktop-shell, который запускает локальный child runtime, биндит случайный loopback-порт, хранит профили и плагины вне каталога установки и валидирует портативные пакеты пресетов [4] [5]. Документация Hermes native Windows демонстрирует provisioning зависимостей, персистентность данных, scheduled startup и оставшееся ограничение POSIX-терминала [6].

Hermes Studio не является безопасным источником для прямого code reuse в NOESIS: лицензия репозитория — Business Source License 1.1, которая разрешает non-commercial использование, но требует отдельной коммерческой лицензии для коммерческого использования или embedding до change date [7]. Остаётся полезным product-design референсом, пока лицензионные условия не будут отдельно решены.

## Сравнение кандидатов

| Источник | Решение по reuse | Чему NOESIS стоит поучиться |
|---|---|---|
| Hermes WebUI | Референс и опциональный protocol client; прямой зависимости в ядре нет | Простой Python/vanilla UI, provider profiles, панели workspace/session, surface для skill/memory, auth и health endpoints |
| DeepSeek Harness | Архитектурный референс; без runtime-копии в ядре | Plugin-швы, упорядоченная композиция profile/bundle, event-backed сессии, явные capability providers и обратимые overlays |
| DSH Desktop | Референс по packaging и lifecycle | Lifecycle child-runtime, случайный loopback-порт, readiness-проверки, per-user данные вне install directory, атомарный импорт пресетов и платформо-специфичный packaging |
| Hermes Studio | Только product-референс, пока не решены BSL/commercial-условия | Информационная архитектура для model/provider management, profiles, workflows, skills, memory, files и surfaces coding-агента |
| Hermes Open WebUI integration | Protocol-референс | OpenAI-совместимый локальный gateway может экспонировать инструменты агента, память и skills, но инструменты исполняются там, где запущен сервер; удалённый UI — это не local execution [8] |

## Целевая архитектура

Ядро остаётся `noesis_harness`, Python stdlib-only, local-first и независимо используемое без браузера. Новая переносимая поверхность — это опциональный адаптер с пятью слоями:

| Слой | Ответственность | Политика зависимостей |
|---|---|---|
| NOESIS UI contract | Версионированные локальные HTTP/JSON/SSE endpoints для health, profiles, models, sessions, tasks, memory, skills, approvals и audit | Python stdlib сервер; никаких provider secrets в payload браузера |
| Runtime supervisor | Запускает и останавливает локальный NOESIS worker, выполняет readiness-проверки, записывает логи, обрабатывает crash/restart и выбирает случайный loopback-порт | Отдельный процесс; без претензии на hardened sandbox; сообщает `unavailable`, где hardening отсутствует |
| Provider adapter registry | OpenAI-совместимый, Ollama, llama.cpp, vLLM, LM Studio, Hermes gateway и DeepSeek Harness endpoints | Только конфигурационные адаптеры; имена моделей и endpoints — данные, а не hard-coded предположения |
| Skill/package manager | Безопасные `.noesisskill` бандлы с manifest, digest, отклонением path traversal/symlink, stage/test/approve через существующий `SkillGate` | Никакого silent executable import; ненадёжные бандлы требуют явного approval |
| Desktop shell | Опциональная Electron- или Tauri-обёртка для Windows/macOS; browser-режим остаётся first-class | Должна быть изолирована от ядра; платформенные артефакты собираются и тестируются по архитектуре |

## Контракт переносимого пакета

Переносимый дистрибутив должен иметь каталог установки, содержащий только неизменяемые runtime-файлы, и отдельный user-data каталог. На Windows корневой data-каталог по умолчанию должен быть под `%LOCALAPPDATA%\\NOESIS`; на macOS — под `~/Library/Application Support/NOESIS`. Явный override `NOESIS_HOME` должен поддерживать USB/SSD portable-режим без встраивания machine-specific путей.

Desktop shell должен запускать child runtime со сгенерированным случайным `127.0.0.1`-портом, ожидать `/health`, открывать UI только после readiness и корректно завершать child по выходу. По умолчанию он не должен биндить `0.0.0.0`. Если LAN-доступ включён явно, UI обязан требовать auth token и показывать security warning.

Каждая установка должна хранить логи, SQLite-состояние, skills, profiles, конфигурацию провайдеров и данные сессий вне каталога установки. Обновления должны заменять runtime-файлы без удаления пользовательских данных. Восстановление должно использовать существующие `BestStateStore`, `FiberStore` и `RecoveryCoordinator`; неуспешный рестарт child должен возвращать явную ошибку и сохранять последнее верифицированное состояние.

## Совместимость моделей и skills

Первый релиз должен принимать любого провайдера, экспонирующего документированный OpenAI-совместимый endpoint или локальный адаптер, реализующий NOESIS provider protocol. Это покрывает локальные серверы, такие как Ollama, llama.cpp, vLLM и LM Studio, а также Hermes или DeepSeek Harness gateway endpoints. Он не должен подразумевать, что все модели поддерживают одинаковые инструменты, длину контекста, vision, structured output или reasoning-функции. UI должен отображать capability metadata и работать fail-soft, когда функция недоступна.

NOESIS skills должны использовать формат, вдохновлённый Hermes skills и DSH presets, но с независимыми manifest и security policy. Бандл должен содержать format version, identifier, объявленные capabilities, source digest, ограничения платформы и человекочитаемые инструкции. Импорт должен стадировать во временный каталог, отклонять absolute paths, parent traversal, backslash traversal и symlinks, запускать static security scanning, затем проходить через `SkillGate` для тестов и явного approval. Существующие skill identifiers никогда не должны быть тихо перезаписаны. DSH `.dshpreset` архивы не должны исполняться или копироваться напрямую; будущий importer может транслировать только их декларативные метаданные после валидации [5].

## Дорожная карта реализации

| Фаза | Результат | Доказательство релиза |
|---:|---|---|
| P0 | Версионированный `NOESIS UI Contract v1` с `/health`, `/models`, `/profiles`, `/sessions`, `/tasks`, `/memory`, `/skills`, `/approvals` и `/audit` | Contract-тесты, schema fixtures, no-secret response scan |
| P1 | Stdlib-локальный web-сервер с vanilla UI shell и loopback-аутентификацией | Windows/macOS smoke-тесты, случайный порт, readiness и clean shutdown |
| P2 | Реестр провайдеров и обнаружение capability моделей | Ollama/llama.cpp/LM Studio/OpenAI-совместимые fixtures, недоступные пути и редактируемые секреты |
| P3 | Безопасный package manager `.noesisskill` | Traversal/symlink/oversize тесты, верификация digest, SkillGate approval и rollback |
| P4 | Переносимая desktop-обёртка | Windows x64 и macOS arm64 smoke-артефакты; миграция user-data и восстановление после сбоя |
| P5-00 | Интеграция DeepSeek Harness + Hermes WebUI для Windows/macOS | Опциональные child-process адаптеры за UI Contract v1; loopback/auth, маппинг provider/model capability, маппинг profile/skill scope, недоступные пути и clean shutdown |
| P5 | Адаптеры Hermes/DeepSeek bridge | Local gateway fixtures, явный tool-scope маппинг, cross-agent leakage тесты и audit events |
| P6 | Release-readiness | Полная регрессия, фиксированные coding-задачи, security corpus, чистый secret scan, инвентаризация лицензий и одобрение владельца |

## Граница интеграции DeepSeek Harness и Hermes WebUI

Интеграция намеренно выполнена как adapter layer, а не форк какого-либо runtime. NOESIS control plane обнаружит явно сконфигурированный локальный Hermes API/WebUI gateway или DeepSeek Harness endpoint, провалидирует его версию и capabilities и экспонирует через UI Contract v1 только нормализованные метаданные model/profile/session. Runtime tools продолжают исполняться в workspace выбранного child runtime; браузер не получает raw provider keys или скрытую память.

На Windows первая цель — нативный loopback child process с явной path normalization и clean shutdown. WSL2 остаётся опциональным режимом совместимости для Hermes WebUI, а не требованием. На macOS цель — нативный child process со случайным loopback-портом и user-data в каталоге platform application-support. Адаптер должен возвращать `unavailable`, когда внешний runtime отсутствует, несовместим или не может предоставить запрошенную capability.

Первые поддерживаемые bridge-режимы: Hermes OpenAI-совместимый API, DeepSeek Harness local Web UI/API, где это позволяет его версионированный контракт, и pure provider mode для Ollama, llama.cpp, vLLM или LM Studio. Адаптер не будет молча трактовать удалённый API как local hands; место исполнения инструментов показывается в capability metadata и audit log.

## Non-goals и границы безопасности

Первый переносимый релиз не будет заявлять hardened sandbox, не будет исполнять модельно-сгенерированный Python in-process, не будет молча устанавливать произвольные плагины, не будет экспонировать provider tokens браузеру и не будет объединять приватную память Hermes/DSH только потому, что два профиля видны в одном UI. Cross-agent sharing остаётся явным, проверяемым по scope и audit-backed.

Desktop-обёртка — это surface дистрибуции, а не граница безопасности. Если пользователю требуется OS-level confinement, NOESIS должен интегрировать независимо верифицированный sandbox-провайдер и сообщать `unavailable`, когда он отсутствует.

## Следующий implementation gate

Следующая кодовая фаза должна реализовать P0: небольшой версионированный stdlib UI contract и `/health`/`/models` read-only адаптер, с последующими contract-тестами. Начинать с Electron или полного dashboard не следует. Это сохраняет ядро переносимым, делает совместимость провайдеров измеримой и предотвращает превращение UI во второй непроверенный agent runtime.

## Источники

1. [Hermes WebUI](https://github.com/nesquena/hermes-webui) — MIT web interface, profiles, providers, memory, skills и Windows/WSL заметки.
2. [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) — официальный DeepSeek plugin-oriented harness.
3. [DeepSeek Harness architecture](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md) — profiles, bundles, plugin seams и event-backed сессии.
4. [DSH Desktop](https://github.com/dataelement/dsh-desktop) — MIT desktop wrapper, lifecycle, loopback и cross-platform packaging.
5. [DSH preset package contract](https://github.com/dataelement/dsh-desktop/blob/main/docs/preset-packages.md) — валидация, атомарный install и trust warnings.
6. [Hermes native Windows guide](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/windows-native.md) — native Windows support и dependency matrix.
7. [Hermes Studio LICENSE](https://raw.githubusercontent.com/EKKOLearnAI/hermes-studio/main/LICENSE) — Business Source License 1.1 и commercial-use restriction.
8. [Hermes Open WebUI integration](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/open-webui) — OpenAI-совместимый gateway и server-side tool execution boundary.