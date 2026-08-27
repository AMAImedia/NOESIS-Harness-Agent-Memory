# P6-01 Branch Protection Audit — 2026-08-17

## Область

Эта заметка фиксирует текущее состояние release-gate для приватного репозитория `AMAImedia/NOESIS-Harness-Agent-Memory`. Никаких изменений branch-protection, visibility, release или workflow settings в ходе этого аудита не выполнялось.

## Подтверждённое состояние репозитория

| Проверка | Результат |
|---|---|
| Репозиторий | `AMAImedia/NOESIS-Harness-Agent-Memory` |
| Visibility | Private (`isPrivate=true`, `visibility=PRIVATE`) |
| Default branch | `main` |
| Локальная ветка | `main`, чистое рабочее дерево |
| Local/remote SHA | `d3694dd26f4fdc8eacb95428417d8645d12c02a8` на обоих |
| Remote | `https://github.com/AMAImedia/NOESIS-Harness-Agent-Memory.git` |

## Существующие CI gates

Workflow `.github/workflows/ci.yml` запускается на push и pull request, таргетирующих `main` и `develop`. Его job `test` — это matrix по Python 3.9, 3.10, 3.11 и 3.12 и выполняет `python -m unittest discover -s tests -v` плюс examples и recall benchmark. Job `lint` выполняет `pyflakes` по `noesis_harness/`, `examples/`, `integrations/` и `benchmarks/`. Job `build` собирает distribution и загружает `dist/*`; зависит от `test`. Job `benchmark` запускается только на push в `main`, зависит от `test` и поэтому не должен использоваться как pull-request required check без изменения workflow.

Workflow `.github/workflows/publish.yml` — только для release или ручного dispatch и публикует в PyPI через защищённое окружение `pypi` с OIDC. Он не должен быть branch-protection required check и не должен запускаться просто из-за открытия pull request.

## Рекомендуемая политика required checks для P6-01

До подтверждения владельцем точной политики не включать branch protection. После подтверждения требовать следующие checks по их точным именам GitHub check, subject to one verification pull request: `Tests (Python 3.9)`, `Tests (Python 3.10)`, `Tests (Python 3.11)`, `Tests (Python 3.12)`, `Lint (pyflakes)` и `Build Distribution`. Не требовать `Benchmarks`, если только выполнение benchmark намеренно не переносится в pull requests. Не требовать `Publish to PyPI`.

Рекомендуемые базовые настройки: требовать pull request перед merge; требовать один approving review; dismiss stale approvals при push новых коммитов; требовать conversation resolution; требовать прохождения status checks перед merge; требовать up-to-date ветки перед merge, только если queue time остаётся приемлемым; блокировать force pushes и branch deletion на `main`; сохранять private visibility репозитория. Admin bypass должен оставаться выключенным для обычных merge, кроме случаев, когда владелец явно выбирает emergency procedure.

## Требуемые решения владельца

| Решение | Предлагаемый default | Статус |
|---|---|---|
| Required approving reviews | 1 | Ожидает владельца |
| Dismiss stale reviews | Enabled | Ожидает владельца |
| Require conversation resolution | Enabled | Ожидает владельца |
| Require branches up to date | Enabled если CI latency приемлема | Ожидает владельца |
| Allow force-push to `main` | Disabled | Ожидает владельца |
| Allow branch deletion | Disabled | Ожидает владельца |
| Admin bypass | Disabled по умолчанию | Ожидает владельца |
| Require signed commits | Optional; включить только если локальный signing workflow владельца готов | Ожидает владельца |
| Required CI checks | Четыре test matrix checks + lint + build | Ожидает владельца |
| Benchmark required on PR | Нет, если только workflow trigger не изменён | Ожидает владельца |
| PyPI publish required on PR | Нет | Ожидает владельца |

## Текущее ограничение платформы

Read-only GitHub API-проверка для `branches/main/protection` вернула HTTP 403 с сообщением: `Upgrade to GitHub Pro or make this repository public to enable this feature.` Никаких настроек не менялось. Следовательно, для этого приватного репозитория под доступным планом branch protection включить нельзя. Репозиторий остаётся private по policy; сделать его public — отдельное решение владельца и не является приемлемым workaround без явного одобрения.

## Следующее безопасное действие

Следующее безопасное действие — получить подтверждение владельца для таблицы выше, сохранить policy в документации и проинспектировать имена check-run одного реального pull request, когда/если branch protection станет доступной. Применение branch protection намеренно отложено, потому что текущий GitHub-план отклоняет его и потому что governance settings нельзя менять без одобрения владельца.
