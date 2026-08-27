# Результат конкурентного бенчмарка — 2026-08-17

## Область

Этот отчёт покрывает только локальную contract lane. Он не претендует на запуск Hermes или OpenCode и не заменяет same-task external A/B. Раннер использует фиксированные NOESIS-тесты, явные бюджеты, без исполнения model-generated кода и без внешних сетевых вызовов.

## Результат

Contract lane завершилась с **10 passed, 0 failed, 0 not-run** на CPython 3.12.3 в текущей песочнице. Полный regression suite завершился с **240 passed**. Покрытые поверхности: task/session state, SSE reconnect, provider invocation, Gatekeeper approval, bounded child execution, executable skills, workspaces, multi-agent claims, HTTP session API и terminal client.

| Lane | Статус | Интерпретация |
|---|---:|---|
| NOESIS contract primitives | 10/10 passed | Локальное доказательство реализации |
| Полный regression suite | 240/240 passed | Локальное доказательство надёжности |
| Hermes external protocol | `not_run` | Внешний процесс не запускался |
| OpenCode external protocol | `not_run` | Внешний процесс не запускался |
| Native Windows Python 3.14 | `not_run` | Нет Windows 3.14 runner |
| Native macOS Python 3.14 | `not_run` | Нет macOS 3.14 runner |

## Требуемый протокол external A/B

Валидное внешнее сравнение должно зафиксировать точные ревизии, model/provider, набор промптов, context budget, tool permissions, sandbox backend, timeout, retry policy и evaluator rubric. Каждая система должна запускаться в disposable workspace. Метрики должны включать task success, patch correctness, approval violations, unauthorized egress, secret exposure, recovery after kill/timeout, token/latency budget и human review burden. Неподдерживаемые или недоступные features должны фиксироваться как `not_run`, а не как ноль ошибок.

## Ссылки

[1]: https://opencode.ai/docs/agents/ "OpenCode agents documentation"
[2]: https://opencode.ai/docs/tools/ "OpenCode tools documentation"
[3]: https://github.com/NousResearch/hermes-agent "Hermes Agent repository"
