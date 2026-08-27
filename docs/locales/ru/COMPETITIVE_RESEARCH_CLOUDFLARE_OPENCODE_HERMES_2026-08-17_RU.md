# Заметки конкурентного исследования — 2026-08-17

## Cloudflare OS

Источник: https://blog.cloudflare.com/cloudflare-os/

Cloudflare описывает agent workspace, объединяющий sessions, persistent state, outputs/files, resource access и изолированный runtime. Платформа сочетает agent workspaces, привязанные к curated context/skills, security/governance framework и платформу модифицируемых приложений. Подчёркивается, что агенты стартуют без доступа и запрашивают доступ к конкретным ресурсам. Доступ представлен типизированными capabilities; credentials остаются вне сгенерированного кода. Серверный код выполняется в Dynamic Worker с глобально отключённой исходящей сетью, клиентский код — в sandboxed browser frame с доступом в интернет только через явные capabilities. Gatekeeper-ы опосредуют сервис-специфичные ресурсы/действия, хранят credentials, применяют policy, записывают наблюдаемые ресурсы и контролируют внешне видимые side effects. Cloudflare также описывает policy, следующую тому, что видел агент, поэтому sharing/hand-off/outbound запросы могут ограничиваться по data provenance.

## Cloudflare Sandbox SDK

Источник: https://developers.cloudflare.com/sandbox/concepts/security/

Официальная security model утверждает, что каждый sandbox запускается в отдельной VM, обеспечивая filesystem, process и network isolation плюс resource limits. Предупреждается, что сессии в одном sandbox видят одни и те же файлы/процессы и рекомендуется использовать отдельный sandbox ID на пользователя. Требуются application-level authentication, input validation, rate limiting и application security. Рекомендуется избегать shell-интерполяции, использовать file APIs, хранить credentials вне sandbox и использовать outbound handlers, чтобы sandbox не получал live credentials. Preview/tunnel URL являются bearer-like путями доступа и требуют application authentication. Эти результаты означают, что NOESIS должен различать текущий bounded process boundary и настоящую VM/OS sandbox и не заявлять эквивалентность без native isolation evidence.

## OpenCode

Источники: https://opencode.ai/docs/agents/ и https://opencode.ai/docs/tools/

OpenCode разделяет primary agents и subagents, включая primary-режимы Build и Plan и subagents General/Explore/Scout. Plan по умолчанию ограничен: edits и bash требуют approval. Права агентов могут быть allow/ask/deny и могут быть pattern-scoped для read, edit, bash, task, external directory, skill, webfetch и других tools. OpenCode поддерживает max steps, model selection per agent, agent switching, subagent invocation, custom tools и MCP servers. Tool system включает bash, edit, write, read, grep, glob, apply_patch, skill, todo, webfetch и др. Это сильный продуктовый benchmark для agent modes, permission UX, scoped tools, plan/build разделения и subagent navigation.

## Hermes

Результат поиска и официальный репозиторий: https://github.com/NousResearch/hermes-agent и https://hermes-agent.nousresearch.com/docs/user-guide/features/skills

Hermes релевантен как reference по persistent memory/skills/gateway. Текущий аудит NOESIS рассматривает Hermes как black-box benchmark и архитектурное вдохновение, кроме случаев, когда проведён аудит конкретного исходного файла и license obligation. Никаких внешних performance claims не делается без запуска фиксированного benchmark протокола.

## Стратегические следствия для NOESIS

Высшая дифференциация — не копировать UI и не добавлять unrestricted tools. NOESIS должен сочетать Cloudflare-стиля observation-aware capabilities и credential isolation, OpenCode-стиля Plan/Build/Explore agent modes и scoped permissions и Hermes-стиля persistent memory/skills/gateway reach с более сильными provenance, rollback и secure-by-default policy. Требуемые дополнения: resource observation lineage, taint-aware outbound policy, typed capabilities с resource scope, отдельный sandbox adapter interface, policy simulation/explainability, безопасные документационные примеры, структурированные prompt-injection holdouts и воспроизводимые external benchmark lanes.

## Выводы по native packaging

Документация PyInstaller утверждает, что bundled interpreter и output зависят от активной ОС, версии Python и архитектуры; Windows или macOS artifact должен собираться на этой ОС под этой версией Python. One-folder mode проще отлаживать, чем one-file. One-file mode распаковывается во временную директорию и может оставить временные файлы после crash; его нельзя запускать с правами администратора на Windows из-за риска подмены shared library во время подготовки. macOS-сборки могут таргетить x86_64, arm64 или universal2, когда host Python это поддерживает; опции code signing — platform-specific. Источники: https://pyinstaller.org/en/stable/operating-mode.html и https://pyinstaller.org/en/latest/usage.html.

Документация Briefcase утверждает, что macOS outputs включают `.app` bundles или Xcode-проекты и могут быть упакованы как DMG, ZIP или PKG; signing и notarization — часть обычного release-пути. Поддерживается Python 3.10+, но native build и signing evidence остаются platform-specific. Источник: https://briefcase.beeware.org/en/stable/reference/platforms/macOS/.

Cloudflare Sandbox SDK — это TypeScript/Workers SDK и не является drop-in Python local runtime. Полезные для NOESIS reusable concepts: per-user sandbox identity, VM/container isolation, resource quotas, streaming, file APIs, outbound handlers, application authentication и explicit cleanup. Репозиторий под Apache-2.0, но его runtime требует собственной Cloudflare/Docker/Node-экосистемы. Источник: https://github.com/cloudflare/sandbox-sdk.

## Новые стратегические приоритеты

1. Добавить observation ledger и taint labels к каждому resource read, output и handoff. Gatekeeper policy должна следовать data provenance, а не только именам tools.
2. Добавить Cloudflare-стиля zero-access startup: каждый агент стартует без resource, network или write capability; capabilities должны быть типизированными, scoped, expiring и видимыми в UI.
3. Добавить provider-independent sandbox adapter interface с backends local bounded process, Docker/Podman, Windows Job Objects/AppContainer и macOS sandbox-exec/profile. Не заявлять эквивалентную изоляцию между адаптерами.
4. Добавить Plan/Build/Explore/Review agent modes и pattern-based permissions, но NOESIS по умолчанию строже: read-only до approval, а не OpenCode-стиля documented default tool enablement.
5. Сделать Web UI operator console: workspace/agent graph, live policy explanation, observation lineage, pending approvals, patch review, provider health, process telemetry и экспортируемый redacted audit.
6. Считать документацию security surface: примеры должны быть copy-paste-safe, использовать argv/file APIs вместо shell-интерполяции, никогда не включать realistic credentials, помечать simulation vs execution и прогонять docs snippets через статический safety linter.
7. Запускать external A/B только в disposable воспроизводимых окружениях с идентичными task prompts, моделями, budgets и side-effect policy. Неподдерживаемые или не запущенные lanes должны быть отмечены.
8. Собирать PyInstaller и Briefcase artifacts раздельно на Windows и macOS Python 3.14 runners, предпочитать onedir для отладки и signed/notarized release artifacts, публиковать SHA-256 плюс SBOM/provenance records.
