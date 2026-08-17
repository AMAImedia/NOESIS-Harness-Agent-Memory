# NOESIS — совместный checklist и TODO

Дата контрольного состояния: **2026-08-17**

Репозиторий: `AMAImedia/NOESIS-Harness-Agent-Memory`

Режим публикации: **Private**

Текущая ветка: `main`

Последний подтверждённый remote commit: `ba9ccce` — `docs: add portable UI integration roadmap`

Текущий рабочий этап: **P0-01/P0-02 реализованы локально; ожидается commit и private remote verification**

## Как мы используем этот документ

Этот файл является общей доской управления проектом. В нём видно, **что уже сделано, что делает агент, что должен подтвердить владелец и по какому доказательству этап считается завершённым**.

Статусы имеют строгое значение. `DONE` ставится только после фактического результата: код или документ сохранён, тест прошёл, benchmark выполнен при необходимости, fail-soft поведение проверено, а commit и remote state подтверждены. `IN PROGRESS` означает, что работа выполняется и ещё не является готовой. `WAITING FOR USER` означает, что требуется решение или доступ владельца. `BLOCKED` означает, что продолжение невозможно без внешнего условия. Нельзя заменять эти статусы предположениями или обещаниями.

Каждая новая функция NOESIS должна проходить одинаковый мини-цикл: **план → реализация → focused tests → benchmark → fail-soft/security check → full regression → documentation → local commit → private remote verification**. Публичный релиз, изменение visibility, подключение внешнего сервиса с учётной записью, публикация секретов или необратительное действие требуют отдельного подтверждения владельца.

## 1. Уже завершено и проверено

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| DONE-01 | Локальный Git baseline и ветка `main` | `DONE` | Protected local baseline и последующие commits сохранены; GitHub push выполняется только в private repository |
| DONE-02 | Private GitHub repository | `DONE` | `AMAImedia/NOESIS-Harness-Agent-Memory`; GitHub API подтвердил `isPrivate=true`, default branch `main` |
| DONE-03 | Nextgen primitives | `DONE` | RunEnvelope, capabilities, audit chain, command ledger, isolation broker, context manager и result envelopes |
| DONE-04 | Governance | `DONE` | Gatekeeper, DAGPlanner, VaultProjector, SkillGate и honest ExecutionLadder |
| DONE-05 | Durable fibers | `DONE` | SQLite checkpoints, monotonic steps, fault-injection recovery и Windows-safe connection cleanup |
| DONE-06 | Evidence memory | `DONE` | Provenance, confidence, freshness decay, duplicate merge, conflicts и review-only consolidation |
| DONE-07 | Security base | `DONE` | Prompt injection, secret/token, invisible Unicode, eval/exec patterns, safe paths и deny-by-default execution contract |
| DONE-08 | Coordination | `DONE` | Dependency-aware claiming, leases, TTL reclaim и duplicate completion suppression |
| DONE-09 | Budgeted context | `DONE` | Hard token cap, priority order, required blocks, dropped-item audit и provenance |
| DONE-10 | Best-state protection | `DONE` | Monotonic best score, verifier gate, explicit rollback, automatic recovery и persisted history |
| DONE-11 | Fiber/lease recovery integration | `DONE` | `FiberStore.restore`, `RecoveryCoordinator`, expired-lease reclaim и live-lease protection; 100/100 crash cycles |
| DONE-12 | Controlled memory A/B | `DONE` | Одинаковый token budget, legacy prefix vs provenance-aware nextgen, recall/transfer/dropped IDs |
| DONE-13 | Trajectory evaluator | `DONE` | C1/C2/C3, peak retention, dips, recovery credit, `avg@3` и `best@3` |
| DONE-14 | Security holdout corpus | `DONE` | 12 fixed cases; n=100 pass rate 1.000000 |
| DONE-15 | Pinned coding-task adapter | `DONE` | 3 pinned tasks, revision `2026-08-17.1`, AST-only verifier и fail-soft `unavailable` dynamic execution |
| DONE-16 | Cross-agent leakage corpus | `DONE` | 8 cases: tenant, recipient, private scope, proposals и unknown agent; n=100 pass rate 1.000000 |
| DONE-17 | Release-readiness audit | `DONE` | `docs/RELEASE_READINESS_AUDIT_2026-08.md`; 118/118 tests passed in 3.097 s; AST audit found 0 actual eval/exec calls |
| DONE-18 | Portable UI research | `DONE` | `docs/PORTABLE_UI_INTEGRATION_ROADMAP.md`; Hermes, DeepSeek Harness, DSH Desktop and Windows-native facts checked; Hermes Studio BSL 1.1 recorded |

## 2. Текущее verified состояние

| Проверка | Результат |
|---|---:|
| Полный regression suite после coding/leakage layers | **118/118 passed in 3.097 s** |
| Pinned coding static pass rate, n=100 | **1.000000** |
| Cross-agent isolation pass rate, n=100 | **1.000000** |
| Dynamic coding execution | **`unavailable` намеренно** |
| Hardened OS-level sandbox | **`unavailable`, не заявляется** |
| Secret-pattern scan | **clean** |
| Actual AST `eval`/`exec` calls in core | **0** |
| Current GitHub visibility | **Private** |
| Branch protection | **Не включена** |

## 3. Активный TODO: Portable Control Plane

### P0 — UI Contract и минимальный local API

#### P0-01 — подробный checklist: versioned UI Contract v1

| Подшаг | Действие | Статус | Доказательство/критерий |
|---|---|---|---|
| P0-01.a | Зафиксировать `contract_version` и совместимость v1 | `DONE` | `CONTRACT_VERSION=1.0`; unsupported version rejected |
| P0-01.b | Описать общую envelope-схему | `DONE` | `UIEnvelope` implements required fields and deterministic JSON |
| P0-01.c | Описать `/health` response schema | `DONE` | `health_payload` plus `docs/UI_CONTRACT_V1.md`; no-secret fields |
| P0-01.d | Описать `/models` response schema | `DONE` | `model_payload` validates id/provider/capabilities and redacts secret-shaped keys |
| P0-01.e | Описать adapter errors | `DONE` | Contract rejects invalid status and distinguishes failure statuses |
| P0-01.f | Добавить JSON fixtures и contract tests | `DONE` | 6 focused P0 tests passed; deterministic serialization and invalid inputs covered |
| P0-01.g | Добавить integration boundary docs | `DONE` | `UI_CONTRACT_V1.md` and Portable UI roadmap define optional Hermes/DeepSeek adapters |

#### P0-02 — подробный checklist: stdlib read-only `/health`

| Подшаг | Действие | Статус | Доказательство/критерий |
|---|---|---|---|
| P0-02.a | Реализовать stdlib HTTP server | `DONE` | `HealthServer` uses `http.server`; no model/tool execution |
| P0-02.b | Bind default to loopback | `DONE` | Default `127.0.0.1`; non-loopback rejected by constructor |
| P0-02.c | Add readiness and capability statuses | `DONE` | Optional Hermes/DeepSeek/sandbox default to `unavailable`; core reports `degraded` |
| P0-02.d | Add request IDs and bounded responses | `DONE` | Request IDs, bounded response guard, no-store/security headers and redaction |
| P0-02.e | Add clean shutdown | `DONE` | Context manager, stop/join and duplicate start tests passed |
| P0-02.f | Add negative tests | `DONE` | POST denied, unknown path invalid_request, invalid binding and duplicate start covered |
| P0-02.g | Add latency benchmark | `DONE` | n=100: error 0.000000; p50 0.744900 ms; p95 22.139500 ms; mean 4.868805 ms |

| ID | Задача | Владелец | Статус | Критерий готовности |
|---|---|---|---|---|
| P0-01 | Описать versioned `NOESIS UI Contract v1` | Агент | `DONE` | `noesis_harness/ui_contract.py`, `docs/UI_CONTRACT_V1.md`, 6 focused tests |
| P0-02 | Добавить read-only `/health` endpoint | Агент | `DONE` | `noesis_harness/health_server.py`, 6 focused tests, n=100 benchmark |
| P0-03 | Добавить read-only `/models` endpoint | Агент | `NEXT` | Contract schema exists; HTTP endpoint remains next substage |
| P0-04 | Сделать stdlib HTTP adapter без обязательного Node/npm | Агент | `TODO` | `http.server` или эквивалент stdlib, deterministic tests и clean shutdown |
| P0-05 | Contract fixtures и no-secret response scan | Агент | `TODO` | JSON fixtures, schema tests, secret scan и invalid-input tests |
| P0-06 | Документация запуска и пример curl/PowerShell | Агент | `TODO` | Команды проверены на Windows-friendly syntax; без PowerShell here-strings |

### P1 — Browser UI и runtime supervisor

| ID | Задача | Владелец | Статус | Критерий готовности |
|---|---|---|---|---|
| P1-01 | Минимальный browser UI: health, models, sessions | Агент | `TODO` | Работает поверх UI Contract, не содержит agent logic и не получает provider secrets |
| P1-02 | Child-runtime supervisor | Агент | `TODO` | Random loopback port, readiness check, log path, clean stop, crash recovery |
| P1-03 | User-data separation | Агент | `TODO` | Runtime files отделены от `%LOCALAPPDATA%\\NOESIS`, `~/Library/Application Support/NOESIS` и `NOESIS_HOME` |
| P1-04 | Auth и LAN warning | Агент | `TODO` | Loopback default, token for non-loopback, explicit warning and negative tests |

### P2 — Models и providers

| ID | Задача | Владелец | Статус | Критерий готовности |
|---|---|---|---|---|
| P2-01 | Provider adapter registry | Агент | `TODO` | OpenAI-compatible, Ollama, llama.cpp, vLLM и LM Studio are represented as adapters |
| P2-02 | Hermes gateway adapter | Агент | `TODO` | Explicit endpoint/key mapping, tool-scope declaration, no remote/local confusion |
| P2-03 | DeepSeek Harness adapter | Агент | `TODO` | Version-pinned optional bridge, plugin capability mapping and fail-soft compatibility |
| P2-04 | Capability-aware model selector | Агент | `TODO` | UI показывает tool/context/vision/structured-output capabilities, unsupported features fail-soft |

### P3 — Skills и portable bundles

| ID | Задача | Владелец | Статус | Критерий готовности |
|---|---|---|---|---|
| P3-01 | `.noesisskill` manifest format | Агент | `TODO` | Format version, ID, digest, declared capabilities, platform constraints and source |
| P3-02 | Safe import pipeline | Агент | `TODO` | Stage → scan → test → approve; rejects absolute paths, traversal, symlinks and oversize |
| P3-03 | Skill rollback | Агент | `TODO` | Failed install leaves prior verified skill intact; audit event recorded |
| P3-04 | Hermes/DSH metadata translator | Агент | `TODO` | Only declarative metadata; no silent execution/import of foreign presets |

### P4–P6 — Desktop, bridges и release

| ID | Задача | Владелец | Статус | Критерий готовности |
|---|---|---|---|---|
| P4-01 | Windows x64 portable artifact | Агент | `TODO` | Install/launch/upgrade/data-preservation smoke test on Windows runner |
| P4-02 | macOS arm64 portable artifact | Агент | `TODO` | Launch, loopback, data preservation and clean shutdown smoke test on macOS runner |
| P4-03 | Optional Electron/Tauri wrapper decision | Владелец + агент | `WAITING FOR USER` | Choose wrapper only after P0–P3 prove the contract; no premature framework lock-in |
| P5-00 | Windows/macOS Hermes WebUI + DeepSeek Harness integration layer | Агент | `TODO` | Optional adapters use the versioned UI contract; Hermes and DeepSeek runtime remain child processes; local loopback, auth, model capability mapping, scope mapping and unavailable paths tested |
| P5-01 | Hermes/DeepSeek integration tests | Агент | `TODO` | Local gateway fixtures, scope mapping, auth, audit and leakage tests |
| P5-02 | Pinned coding-task expansion | Агент | `TODO` | Expand only after the current 3-task adapter remains stable under repeated regression |
| P6-01 | Branch protection | Владелец + агент | `WAITING FOR USER` | Owner confirms required checks/review policy; private repository remains unchanged |
| P6-02 | Public release decision | Владелец | `WAITING FOR USER` | Explicit owner approval after release audit; no automatic visibility change |

## 4. Как устроена документация проекта

Чтобы не потеряться среди документов, используется не один огромный файл, а короткая иерархия с одним индексом:

| Уровень | Файл | Назначение |
|---|---|---|
| 1 | `docs/PROJECT_CHECKLIST_TODO_RU.md` | Главный operational checklist: что делать сейчас, кто отвечает и какое доказательство нужно |
| 2 | `docs/README.md` | Навигационный индекс всех документов |
| 3 | `docs/PLAN_NOESIS_1.0_MASTER.md` | Архитектурные фазы и долгосрочные gates |
| 4 | `docs/PORTABLE_UI_INTEGRATION_ROADMAP.md` | Отдельный план Portable Control Plane и Hermes/DeepSeek adapters |
| `docs/UI_CONTRACT_V1.md` | Точная versioned схема envelope, `/health`, `/models`, errors и redaction |
| 5 | `docs/ARCHITECTURE_1.0_NEXTGEN.md` и `docs/EVALUATION_PROTOCOL.md` | Детали архитектуры и измерений |
| 6 | `docs/IMPLEMENTATION_REPORT_2026-08.md` и `docs/RELEASE_READINESS_AUDIT_2026-08.md` | Фактические результаты, commits, tests и release gates |

Правило: текущий статус и следующий шаг всегда смотрим в checklist; детали реализации — в профильном документе; факты завершения — в implementation report/audit. Поэтому объединять всё в один гигантский Markdown-файл не нужно.

## 5. Что нужно от владельца

| ID | Вопрос/решение | Статус |
|---|---|---|
| USER-01 | Подтвердить приоритет P0: сначала local API contract, а не сразу большой desktop UI | `CONFIRMED BY CONTINUATION` |
| USER-02 | Выбрать первыми provider targets: Ollama, LM Studio, llama.cpp, vLLM, Hermes или DeepSeek Harness | `OPTIONAL INPUT` |
| USER-03 | Позже выбрать Electron или Tauri после P0–P3 | `WAITING` |
| USER-04 | Отдельно подтвердить branch protection | `WAITING` |
| USER-05 | Отдельно подтвердить public release; до этого repository остаётся private | `WAITING` |

Отсутствие ответа владельца не блокирует P0-01 и P0-02. Агент может продолжать безопасные локальные работы, но не должен самостоятельно менять visibility, подключать коммерчески ограниченный код, публиковать секреты или объявлять hardened sandbox.

## 6. Ближайший action gate

**Следующее действие агента:** реализовать `P0-03` — read-only `/models` HTTP endpoint поверх уже готового `model_payload`, затем добавить provider registry fixtures. P0-01/P0-02 уже прошли focused tests и full regression.

**Следующее действие владельца:** можно написать **«продолжай P0»**; для P0-03 не требуется новый доступ. Если нужны другие providers в первом приоритете, перечислите их; это изменит порядок `P2` без изменения security boundaries.

## 7. Правило обновления

После каждого этапа агент обновляет этот файл в том же commit, где находится изменение, и указывает: что сделано, какой тест прошёл, какой benchmark выполнен, какой статус fail-soft проверен, какой commit опубликован в private remote и какой следующий gate активен.
