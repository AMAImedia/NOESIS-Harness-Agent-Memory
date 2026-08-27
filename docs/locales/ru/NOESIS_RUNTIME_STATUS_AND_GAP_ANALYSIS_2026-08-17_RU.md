# NOESIS runtime status и gap analysis — 2026-08-17

## Главный вывод

NOESIS-Harness-Agent-Memory сейчас — это **stdlib-first durable memory и coordination kernel с portable read-only control plane**. Это ещё не готовое интерактивное agent-приложение уровня Manus, Claude Code, OpenCode или Hermes Desktop. Репозиторий намеренно реализует фундамент безопасности и управления состоянием до включения model/tool execution.

## Почему Python 3.14 не является baseline

Package metadata объявляет `requires-python = ">=3.9"`, а CI-matrix покрывает Python 3.9, 3.10, 3.11 и 3.12. README идентифицирует Python 3.11 как текущий верифицированный laptop runtime. Это политика совместимости, а не заявление о том, что Python 3.14 нежелателен.

Использование Python 3.14 как единственного portable baseline сузило бы совместимость и потребовало бы полного verification pass на Windows и macOS. Ядро намеренно использует стабильные standard-library APIs и SQLite WAL, чтобы один и тот же код мог работать на старых поддерживаемых версиях Python. Корректный подход — добавить Python 3.14 как **дополнительный CI и compatibility target**, верифицировать его на native Windows/macOS runners, и только после этого рассматривать смену minimum или recommended runtime. В текущей песочнице установлен только Python 3.12, и там проходит 200-тестовый suite; Python 3.14 не верифицирован.

Второе важное различие: текущий portable launcher portable по install/data layout и process boundary, но всё ещё требует совместимый Python runtime. Это пока не self-contained single-file Windows `.exe` или macOS `.app`, бандлящий Python.

## Что реально делает текущая portable-система

| Компонент | Реализованное поведение | Что ещё не реализовано |
|---|---|---|
| `portable_launcher.py` | Раздельные install/data roots, `NOESIS_HOME`, platform-specific data placement, loopback control plane, startup probe и persistence sentinel | Нет model invocation, нет исполнения skill entrypoint, нет package installer, нет требования Node/npm |
| `health_server.py` | Read-only `GET /`, `/ui`, `/health`, `/models`; loopback по умолчанию; опциональный authenticated LAN mode; bounded JSON; CSP и no-store headers | Нет POST command API, нет session mutation, нет model invocation endpoint |
| Embedded Web UI | Self-contained HTML, показывающий health, models, capabilities и read-only sessions inventory; invocation button отключён | Нет chat, streaming, tool approval, task editor, diff viewer, кнопки запуска агента или skill runner |
| `runtime_supervisor.py` | Запускает предоставленный владельцем child `argv`, назначает случайный loopback-порт, опрашивает `/health`, пишет логи, выполняет bounded crash recovery и clean stop | Не выбирает модель, не интерпретирует вывод модели, не генерирует команды, не решает, какой агент/skill запускать |
| `skill_import.py` + `skill_store.py` | Stages, scans, verifies digest, approves, installs immutable versions, updates active pointer transactionally и rolls back | Никогда не импортирует Python-модули и не исполняет skill entrypoints; нет UI-driven skill execution |
| Core memory/coordination | SQLite durability, evidence/provenance, bounded context, leases, recovery, best-state protection и cross-agent scope checks | Нет claim на OS-level sandbox или hardened remote execution |

Прямой ответ на «можно ли сейчас запускать agents и skills?» таков: **supervisor может запустить явно указанный локальный child runtime, но portable Web UI пока не может запустить интерактивный model agent; skill system может безопасно import/install/rollback скиллы, но намеренно не может исполнять их код.** Это намеренная граница безопасности, а не случайно отсутствующая кнопка.

## Сравнение с reference-продуктами

| Capability | NOESIS текущее состояние | OpenCode | Claude Code | Hermes Agent |
|---|---|---|---|---|
| Interactive coding agent | Не включён в текущем Web UI | Terminal, desktop app и IDE extension; читает код, планирует и вносит изменения [1] | Terminal, IDE, desktop и web surfaces; читает код, редактирует файлы и запускает команды [2] | Interactive CLI/TUI и gateway [3] |
| Model/tool execution | Явно недоступно в coding adapter и UI | Core product capability [1] | Core product capability [2] | Core product capability [3] |
| Persistent memory | Сильный experimental/verified kernel: provenance, bounded context, recovery и A/B evaluation | Продукт-специфичный context/configuration; не та же NOESIS memory model | Auto memory, `CLAUDE.md`, skills и hooks [2] | Curated persistent memory, session search и learning journey [4] |
| Skill execution/self-improvement | Только safe manifest/import/store/rollback; execution намеренно отключён | Custom commands/configuration [1] | Skills, hooks и custom agents [2] | Skills можно просматривать/использовать; агент имеет learning loop [3] [4] |
| Multi-agent coordination | Leases, dependency-aware claiming, non-overlap и recovery primitives | Agent modes и coding workflow [1] | Agent teams/background agents и Agent SDK [2] | Delegates и parallel subagents [3] |
| Desktop/Web UI | Read-only локальный control plane, не продуктовый UI | Desktop/IDE/TUI surfaces [1] | Desktop/web/IDE/terminal surfaces [2] | CLI/TUI/gateway/desktop ecosystem [3] |
| Security posture | Консервативный deny-by-default, AST-only verification, без claim на OS sandbox | Execution-oriented продукт со своими permissions и runtime model | Execution-oriented продукт с permissions, hooks и tool integrations | Execution-oriented продукт с tools, gateways и remote backends |

Сравнение показывает, что NOESIS сейчас не «лучший в мире» как полный agent-продукт. У него потенциально отличительный фундамент — **verifiable memory, явная provenance, durable recovery, non-overlapping multi-agent ownership и консервативные execution boundaries**, — но не хватает интерактивной execution surface и реальных benchmark-доказательств, необходимых для world-leading claim.

## Честный статус проекта

Самый точный статус: **release-candidate ядро для local-first security-oriented agent OS foundation; portable read-only control plane верифицирован; интерактивный agent runtime и executable skills — будущие gated components.** Репозиторий имеет доказательства: 200 passing tests, чистый release audit, ноль фактических AST `eval`/`exec` вызовов в core и recall benchmark accuracy 1.00 в определённом локальном benchmark. Эти результаты не устанавливают превосходства над продуктами с другими scopes, более крупными экосистемами или production-scale оценками.

## Что нужно построить для приближения к запрошенному продуктовому уровню

Следующий продуктовый слой следует реализовать за явными capability gates: versioned task/session command API, реальный интерактивный chat и streaming surface, per-agent workspaces, provider invocation adapters, approval-aware tool execution, diff/patch review, executable skills в отдельном sandboxed child runtime, session resume, agent-team orchestration и native Windows/macOS packaging. Каждый feature требует сфокусированных security tests, failure recovery tests и cross-platform verification до того, как он будет назван portable.

Безопасное архитектурное направление — сохранять stdlib control plane как source of truth и добавлять execution как изолированный optional layer. Будущий Tauri shell может обеспечить native packaging, но сам по себе не создаст недостающий agent runtime и не сделает систему безопасной. Python 3.14 следует добавлять как проверенный compatibility target, а не заменять преждевременно текущий `>=3.9` контракт.

## Ссылки

[1]: https://opencode.ai/docs/ "OpenCode documentation"

[2]: https://code.claude.com/docs/en/overview "Claude Code overview"

[3]: https://github.com/NousResearch/hermes-agent "Hermes Agent repository"

[4]: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory "Hermes Agent persistent memory"
