# NOESIS — совместный checklist и TODO

Дата контрольного состояния: **2026-08-17**

Репозиторий: `AMAImedia/NOESIS-Harness-Agent-Memory`

Режим публикации: **Private**

Текущая ветка: `main`

Последний подтверждённый remote commit: `66eb5be` — `docs: record desktop wrapper decision memo`

Текущий рабочий этап: **release-readiness audit remote verified; P4-03 decision memo ready; следующий gate — owner decisions по branch protection, native runners, wrapper и public release**

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
| Branch protection | **Не включена; GitHub API HTTP 403: plan upgrade or public repository required** |

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
| P0-01 | Описать versioned `NOESIS UI Contract v1` | Агент | `DONE / REMOTE VERIFIED` | `noesis_harness/ui_contract.py`, `docs/UI_CONTRACT_V1.md`, 6 focused tests, commit `f1e1c91` |
| P0-02 | Добавить read-only `/health` endpoint | Агент | `DONE / REMOTE VERIFIED` | `noesis_harness/health_server.py`, 6 focused tests, n=100 benchmark, commit `f1e1c91` |
| P0-03 | Добавить read-only `/models` endpoint | Агент | `DONE / REMOTE VERIFIED` | `ProviderRegistry`, five fixtures, `/models` HTTP tests, no-secret scan, benchmark, commit `a6ad64a` |
| P0-04 | Сделать stdlib HTTP adapter без обязательного Node/npm | Агент | `DONE / REMOTE VERIFIED` | `HealthServer` + `/health` + `/models` use stdlib only; commit `a6ad64a` |
| P0-05 | Contract fixtures и no-secret response scan | Агент | `DONE / REMOTE VERIFIED` | 6 provider tests, metadata-only assertions, explicit unavailable state, commit `a6ad64a` |
| P0-06 | Документация запуска и пример curl/PowerShell | Агент | `DONE / LOCAL VERIFIED` | `examples/run_control_plane.py`, curl/PowerShell examples, Windows launcher smoke test: `/health` and `/models` returned contract `1.0`; commit/remote verification pending |
| P0-07 | Capability-aware Hermes/DeepSeek bridge discovery | Агент | `DONE / LOCAL VERIFIED` | Read-only `/health` + `/models` probes; ready, unavailable, degraded and unreachable cases: 4/4 focused tests passed; commit/remote verification pending |

### P1 — Browser UI и runtime supervisor

Следующий execution order: сначала минимальный static browser UI поверх `/health` и `/models`, затем child-runtime supervisor с random loopback port и readiness checks; session mutation и model invocation остаются вне P1 до отдельного contract/security review.

| ID | Задача | Владелец | Статус | Критерий готовности |
|---|---|---|---|---|
| P1-01 | Минимальный browser UI: health, models, sessions | Агент | `DONE / REMOTE VERIFIED` | `/` и `/ui` self-contained HTML; health/models fetch; sessions panel read-only; 2/2 focused tests; CSP/no-store/no-secret assertions; commit `573ba90`; remote SHA `573ba909df7d9b0d8b1cd7d2c2b2805b1885da99`; repository remains private |
| P1-02 | Child-runtime supervisor | Агент | `DONE / REMOTE VERIFIED` | `runtime_supervisor.py`: random loopback port, readiness GET, per-runtime append log, clean stop, bounded crash recovery; 3/3 focused Windows tests; 139/139 full tests; commit `845a7a1`; remote SHA `845a7a1c0b5980d07bc559a4d2adb121eb7c7ec6`; repository remains private |
| P1-03 | User-data separation | Агент | `DONE / REMOTE VERIFIED` | `user_data.py` resolves explicit `NOESIS_HOME`, Windows `%LOCALAPPDATA%\\NOESIS`, macOS `~/Library/Application Support/NOESIS`; creates runtime/state/logs/cache/config outside source tree; 5/5 focused tests; 144/144 full tests; commit `4046605`; remote SHA `4046605814a5aa296d25229ff392495c2d733f14`; repository remains private |
| P1-04 | Auth и LAN warning | Агент | `DONE / REMOTE VERIFIED` | Loopback default; non-loopback requires explicit opt-in, >=16-char bearer token and warning acknowledgement; missing/wrong auth returns 401; 3/3 focused tests; 147/147 full tests; commit `4e73445`; remote SHA `4e73445fa3278342f83c42a8f404bf6cc0eed088`; repository remains private |

### P2 — Models и providers

| ID | Задача | Владелец | Статус | Критерий готовности |
|---|---|---|---|---|
| P2-01 | Provider adapter registry | Агент | `DONE / REMOTE VERIFIED` | Canonical declarative specs for OpenAI-compatible, Ollama, llama.cpp, vLLM, LM Studio plus bridge kinds; capability schema and auth modes; no network calls/credentials; 8/8 focused provider tests; 149/149 full tests; commit `052a0cf`; remote SHA `052a0cfa976c273bde3989e8dcaa622c3c627af2`; repository remains private |
| P2-02 | Hermes gateway adapter | Агент | `DONE / REMOTE VERIFIED` | Version-pinned declarative adapter; explicit local/remote separation; credential reference only; bounded tool scopes; no network/model execution; 4/4 focused tests; 153/153 full tests; commit `130d51e`; remote SHA `130d51ea80046821f42478d2522385bb3b2180a6`; repository remains private |
| P2-03 | DeepSeek Harness adapter | Агент | `DONE / REMOTE VERIFIED` | Version-pinned optional bridge/plugin; explicit local/remote separation; credential reference only; canonical plugin capability mapping; degraded/incompatible/unavailable states; 6/6 focused tests; 159/159 full tests; commit `9471acb`; remote SHA `9471acbf77141daa2843e97dac9fde029082a7a3`; repository remains private |
| P2-04 | Capability-aware model selector | Агент | `DONE / REMOTE VERIFIED` | Deterministic metadata-only selector; preferred-provider tie-break; ready/degraded/incompatible/unavailable states; UI capability badges with invocation disabled; 5/5 focused tests; 164/164 full tests; commit `e02fbbf`; remote SHA `e02fbbf24b2df461136ddb3c28ca9273251c8bcc`; repository remains private |

### P3 — Skills и portable bundles

| ID | Задача | Владелец | Статус | Критерий готовности |
|---|---|---|---|---|
| P3-01 | `.noesisskill` manifest format | Агент | `DONE / REMOTE VERIFIED` | Strict format v1.0 with ID/version/digest/capabilities/platforms/provenance; canonical JSON; traversal/symlink/secret-key rejection; 6 tests passed, symlink case skipped only when Windows cannot create symlink; remote SHA `d7844be5cf41653ceef08e5414ba5282d9d78bde`; repository remains private |
| P3-02 | Safe import pipeline | Агент | `DONE / REMOTE VERIFIED` | Stage → scan → test hook → approve; rejects missing/tampered digest, traversal, symlinks and oversize; never imports/executes entrypoint; 5/5 focused tests; 175/175 full tests; commit `ca59e18`; remote SHA `ca59e1850282c8ec2c3841a7cda272ed95be2ef5`; repository remains private |
| P3-03 | Skill rollback | Агент | `DONE / REMOTE VERIFIED` | Transactional versioned install/upgrade; failed approval/install leaves active verified version unchanged; rollback selects previous verified version; append-only audit JSONL; 3/3 focused tests; 178/178 full tests; commit `f103503`; remote SHA `f1035035ccfe1fbcb96c7691885f6d796766c428`; repository remains private |
| P3-04 | Hermes/DSH metadata translator | Агент | `DONE / REMOTE VERIFIED` | Whitelist-only declarative translation for Hermes/DeepSeek; config re-validation; dropped-field reporting; rejects presets/commands/system prompts/secrets/unsafe scopes; 5/5 focused tests; 183/183 full tests; commit `27bb5d6`; remote SHA `27bb5d69a4a89b6727ac290150a301aecc2690eb`; repository remains private |

### P4–P6 — Desktop, bridges и release

| ID | Задача | Владелец | Статус | Критерий готовности |
|---|---|---|---|---|
| P4-01 | Windows x64 portable artifact | Агент | `DONE / REMOTE VERIFIED` | Stdlib-only portable launcher; separate install/data roots; explicit NOESIS_HOME override; loopback startup probe; data sentinel survives clean stop; external bind rejected; 4/4 focused tests; 187/187 full tests; commit `75fcd87`; remote SHA `75fcd8729eb0d5e3fe75eb2176bd50a83cb4db2a`; repository remains private |
| P4-02 | macOS arm64 portable artifact | Агент | `DONE / SIMULATED VERIFIED` | macOS `~/Library/Application Support/NOESIS` branch; explicit NOESIS_HOME override; loopback startup; data preservation; clean shutdown; 4/4 platform-simulated tests; 191/191 full tests; actual macOS arm64 runner still unavailable; commit `8fc6561`; remote SHA `8fc65612af2cefbbc1e2bb974a5b493a9c5484de`; repository remains private |
| P4-03 | Optional Electron/Tauri wrapper decision | Владелец + агент | `DECISION MEMO READY / WAITING FOR USER` | Recommendation: keep stdlib-first control plane as canonical baseline; defer wrapper; if native shell is required, prefer isolated optional Tauri layer after native CI and IPC/security review; Electron not default; memo `docs/DECISION_MEMO_P4-03_DESKTOP_WRAPPER_2026-08-17.md` |
| P5-00 | Windows/macOS Hermes WebUI + DeepSeek Harness integration layer | Агент | `DONE / REMOTE VERIFIED` | `BridgeIntegrationCoordinator` registers validated Hermes/DeepSeek declarations; discovery is explicit read-only; loopback/auth/capability/scope mapping and unavailable paths are fail-soft; child runtime is never started implicitly; 4/4 focused tests; 195/195 full tests; commit `a487e4c`; remote SHA `a487e4cd5333fcb2c5d4b1edcf72c763ede00a1a`; repository remains private |
| P5-01 | Hermes/DeepSeek integration tests | Агент | `DONE / REMOTE VERIFIED` | Local stdlib gateway fixtures for Hermes/DeepSeek; auth and readiness probes; audit JSONL without credential/payload leakage; per-agent audit identity; 4/4 focused tests; 199/199 full tests; commit `36c5d2d`; remote SHA `36c5d2dfe6a23ec863344fe273ef1f2c20eece60`; repository remains private |
| P5-02 | Pinned coding-task expansion | Агент | `DONE / REMOTE VERIFIED` | Expanded static AST corpus from 3 to 5 pinned tasks; added CSV parsing and secret redaction tasks; forbidden imports (`subprocess`, `ctypes`, `pickle`, `marshal`, `socket`) denied; dynamic execution remains `unavailable`; 5/5 focused tests; 200/200 full tests; commit `228d1b3`; remote SHA `228d1b35bef2fb27c5cfa0f4ec6573a3bbb57803`; repository remains private |
| P6-01 | Branch protection | Владелец + агент | `AUDIT READY / PLATFORM BLOCKED / WAITING FOR USER` | Audit `docs/P6-01_BRANCH_PROTECTION_AUDIT_2026-08-17.md`; proposed checks: four Python matrix checks + lint + build; benchmark and PyPI publish are not required; owner confirms review policy; private repository remains unchanged |
| P6-02 | Public release decision | Владелец | `WAITING FOR USER` | Explicit owner approval after release audit; no automatic visibility change |

## 5. Release-readiness audit 2026-08-17

| Проверка | Результат |
|---|---:|
| Local/remote SHA consistency | `PASS`; current remote commit `d3694dd26f4fdc8eacb95428417d8645d12c02a8` |
| Private visibility | `PASS`; repository remains private |
| Full regression | `200/200 passed` |
| Recall benchmark | `20/20`, accuracy `1.00` |
| AST syntax errors | `0` |
| Actual AST `eval`/`exec` calls in core | `0` |
| Non-fixture secret-like hits | `0` |
| Synthetic security holdout markers | `1 expected fixture` in `security_holdouts.py` |
| Native macOS arm64 runner | `UNAVAILABLE`; simulated verification only |
| Hardened OS-level sandbox | `UNAVAILABLE`; not claimed |

Подробный memo: `docs/RELEASE_READINESS_AUDIT_2026-08-17.md`. Visibility не изменялась; branch protection, native runner verification, wrapper choice и public release остаются решениями владельца.

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
| 7 | `docs/GITHUB_FREE_PRIVATE_LIMITS_AND_NEXT_TASKS_2026-08-17.md` | Ограничения GitHub Free/private и порядок задач, не зависящих от платных функций |
| 8 | `docs/NOESIS_RUNTIME_STATUS_AND_GAP_ANALYSIS_2026-08-17.md` | Фактическая граница portable control plane, Python policy, Web UI, skills и interactive runtime gaps |

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

**Следующее действие агента:** продолжить доступное без оплаты hardening и начать отдельный product-layer design: versioned task/session command API, interactive chat/streaming contract, approval-aware tool execution и isolated executable-skill runtime; Python 3.14 добавить как дополнительный compatibility target после native verification.

**Следующее действие владельца:** при желании выбрать порядок из доступных задач; отдельно решить, нужен ли будущий upgrade/organization plan для branch protection. До этого никаких public visibility или billing changes не требуется.

## 7. Правило обновления

После каждого этапа агент обновляет этот файл в том же commit, где находится изменение, и указывает: что сделано, какой тест прошёл, какой benchmark выполнен, какой статус fail-soft проверен, какой commit опубликован в private remote и какой следующий gate активен.
