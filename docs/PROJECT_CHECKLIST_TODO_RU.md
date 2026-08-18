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

### P7–P13 — Python 3.14 execution-layer roadmap

| ID | Задача | Владелец | Статус | Критерий готовности |
|---|---|---|---|---|
| P7-01 | Versioned task/session command API | Агент | `IMPLEMENTED / LOCAL VERIFIED` | `task_session_api.py`: schema `noesis.task-session.v1`, append-only idempotent commands, state transitions, resume, message redaction; 4 focused tests; 204/204 full tests on local Python 3.12; Python 3.14 verification pending |
| P7-02 | Interactive chat/streaming contract | Агент | `IMPLEMENTED / LOCAL VERIFIED / PARITY SMOKE ADDED` | `session_stream.py`: schema `noesis.session-stream.v1`, bounded SSE events, Last-Event-ID reconnect cursor, cancellation token; local parity runner confirms monotonic SSE and reconnect evidence on Python 3.14.7 |
| P8-01 | Provider invocation adapters | Агент | `IMPLEMENTED / LOCAL VERIFIED / APPROVAL LAYER DONE` | `provider_invocation.py`: explicit OpenAI-compatible DeepSeek/Hermes call, pinned model, capability gates, credential resolver only at invocation, bounded request/response, structured non-executing output; 3 focused tests; 211/211 full tests on local Python 3.12; Python 3.14 verification pending |
| P8-02 | Capability-aware approval/Gatekeeper | Агент | `IMPLEMENTED / LOCAL VERIFIED` | `gatekeeper.py`: schema `noesis.gatekeeper.v1`, typed capabilities, simulated dry-run, approval/rejection/commit state machine, argument redaction, append-only audit; 5 focused tests; 216/216 full tests on local Python 3.12; Python 3.14 verification pending |
| P9-01 | Isolated child execution runtime | Агент | `IMPLEMENTED / LOCAL VERIFIED / BACKEND CONFORMANCE HARDENED` | `child_execution.py`: explicit Gatekeeper commit, argv allowlist, shell=false, workspace containment, symlink/traversal rejection, environment allowlist, timeout/output budgets, process termination/recovery; optional explicit `SandboxBackend` integration returns `sandboxed:true` only for selected backend execution and fails closed when unavailable. `sandbox_bwrap.py`: Linux/Bubblewrap backend with explicit network unshare and workspace bind. `sandbox_macos.py`: macOS deny-by-default sandbox-exec backend, Linux reports `not_run`. `sandbox_backend.py`: shared conformance schema; `scripts/run_sandbox_conformance.py` writes `docs/SANDBOX_BACKEND_CONFORMANCE_EVIDENCE.json` (SHA-256 `8b9e6fa471183a234d82a9b37304b907749293eee8c9fd8bb019699a5e0c37ba`). 18 focused child/backend tests. Linux command conformance `passed`; macOS/Windows `not_run` on non-native host. `process_control.py` adds POSIX TERM→KILL process-group termination and Windows `taskkill /T /F` fallback. Non-cooperative descendant timeout regression is covered. `scripts/run_task_execution_parity.py` now proves local session/task → approval → child → SSE → recovery flow; evidence `docs/TASK_EXECUTION_PARITY_EVIDENCE.json`. |
| P9-02 | Executable skill runtime | Агент | `IMPLEMENTED / LOCAL VERIFIED / HARDENED SANDBOX NEXT` | `skill_runtime.py`: active immutable version lookup, manifest/platform/digest verification, explicit `skill.execute` manifest capability, Gatekeeper committed target match, disposable bundle workspace and child-only entrypoint execution; `skill_discovery.py`: read-only OpenCode-compatible `SKILL.md` discovery, strict frontmatter/name validation, deterministic digest, explicit allow/deny/ask visibility; 4 discovery tests + existing runtime tests. Parent process never imports or executes skill code. |
| P10-01 | Diff/patch review and per-agent workspaces | Агент | `IMPLEMENTED / LOCAL VERIFIED / MERGE AUTHORIZATION HARDENED` | `workspaces.py`: isolated per-agent roots, safe paths, immutable marker, SHA-256 snapshots, added/modified/deleted patch proposal, approved/rejected review and explicit `authorize_merge` receipt requiring independent reviewer and fresh base; merge authorization never publishes changes. 6 focused tests. |
| P10-02 | Session resume and real multi-agent execution | Агент | `IMPLEMENTED / LOCAL VERIFIED / PROVIDER EXECUTION NEXT` | `multi_agent_runtime.py`: registered agent identities, exclusive task claims, per-agent workspace assignment, review completion, handoff and resume view; `parallel_agent.py`: cooperative `CancellationToken`, deadline budget and explicit `cancelled` result/audit semantics; 2 cancellation regression tests. `experience_reuse.py`: provenance-required bounded reuse, scope/sensitivity denial, deterministic success/recency ordering and explainable char/item budgets. Parallel provider execution remains next; non-cooperative child process cancellation is locally hardened through `process_control.py` (POSIX process groups, Windows task-tree fallback), while native Windows/macOS execution evidence remains blocked on matching hosts. |
| P11-01 | Terminal/Web/desktop surfaces | Агент | `WEB + TERMINAL LOCAL VERIFIED / DESKTOP NEXT` | `health_server.py` + `ui_assets.py` + `portable_launcher.py`: optional durable session create/resume/message API, bounded SSE events, local interactive console, default read-only fallback and loopback/LAN auth preserved; 230/230 full tests on local Python 3.12; Python 3.14 verification pending. `terminal_client.py` provides create/resume/send CLI over the same API; 1 focused integration test; 231/231 full tests on local Python 3.12. Native shell remains next. |
| P12-01 | Native Python 3.14 packaging | Агент | `SOURCE ARTIFACT IMPLEMENTED / NATIVE GATE BLOCKED` | `scripts/build_portable_artifact.py` builds source-portable ZIP with `PORTABLE_MANIFEST.json`, SHA-256 entries and model/secret exclusions. `scripts/verify_python314.py` fail-closed: current sandbox 3.12.3 -> `ok:false`; native `.exe/.app`, embedded 3.14 and Windows/macOS evidence require native 3.14 environment. |
| P13-01 | Comparative A/B and task benchmarks | Агент | `CONTRACT PROTOCOL + LOCAL BASELINE READY / EXTERNAL A-B NOT RUN` | `docs/COMPETITIVE_BENCHMARK_PROTOCOL_RU.md` defines fixed task suite, metrics, stop conditions and reporting schema. `docs/TASK_EXECUTION_PARITY_EVIDENCE.json` records local-only parity `passed`; `scripts/pinned_lane_orchestrator.py` and `docs/PINNED_EXTERNAL_LANE_MATRIX_EVIDENCE.json` prepare connector-neutral Hermes/OpenCode/DeepSeek Harness lanes; external runs and native Windows/macOS measurements remain explicitly `not_run`. |

## 5. Release-readiness audit 2026-08-17

Итоговый отчёт: `docs/FINAL_SECURITY_RELIABILITY_PACKAGING_AUDIT_2026-08-17.md`. Локальный RC verified: 234/234 tests, 10/10 contract benchmark cases, AST eval/exec audit clean, local/remote SHA совпадают. Python 3.14 и native Windows/macOS evidence пока заблокированы отсутствием соответствующей среды; hardened OS sandbox и external A/B также не заявляются как готовые.

| Проверка | Результат |
|---|---:|
| Local/remote SHA consistency | `PASS`; current remote commit `e3ad5101a605686929cf4b07c318a935de0db0af` |
| Private visibility | `PASS`; repository remains private |
| Full regression | `200/200 passed` |
| Recall benchmark | `20/20`, accuracy `1.00` |
| AST syntax errors | `0` |
| Actual AST `eval`/`exec` calls in core | `0` |
| Non-fixture secret-like hits | `0` |
| Synthetic security holdout markers | `1 expected fixture` in `security_holdouts.py`; corpus expanded to 18 cases; pass rate `1.00` |
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
| 9 | `docs/PYTHON_314_ONLY_MIGRATION_2026-08-17.md` | Python 3.14-only policy, CI/native/package release gates и последствия breaking compatibility change |
| 10 | `docs/EXTERNAL_AGENT_OS_INTEGRATION_AUDIT_2026-08-17.md` | License/provenance/security audit Cloudflare OS, Cloudflare Sandbox SDK, Hermes, OpenCode и правила интеграции |
| 11 | `THIRD_PARTY_NOTICES.md` и `docs/third_party_provenance.json` | Обязательные notices, provenance manifest и запрет неаудированного vendoring |

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

**Следующее действие агента:** зафиксировать integration boundaries по external audit и начать P7-01 versioned task/session command API; затем перейти к P8 provider approval gates и P9 child execution runtime. Python 3.14 теперь является единственным целевым runtime; native verification остаётся release gate.

**Следующее действие владельца:** при желании выбрать порядок из доступных задач; отдельно решить, нужен ли будущий upgrade/organization plan для branch protection. До этого никаких public visibility или billing changes не требуется.

## 7. Правило обновления

После каждого этапа агент обновляет этот файл в том же commit, где находится изменение, и указывает: что сделано, какой тест прошёл, какой benchmark выполнен, какой статус fail-soft проверен, какой commit опубликован в private remote и какой следующий gate активен.

## 6. Competitive strategy update 2026-08-17

| Новый gate | Статус | Фактический результат |
|---|---|---|
| Cloudflare/OpenCode/Hermes research | `RESEARCHED / ROADMAP UPDATED` | Сохранены официальные findings и источники в `docs/COMPETITIVE_RESEARCH_CLOUDFLARE_OPENCODE_HERMES_2026-08-17.md`; стратегический roadmap — `docs/STRATEGIC_ROADMAP_BEYOND_COMPETITORS_RU_2026-08-17.md` |
| Cloudflare-style operator UI | `IMPLEMENTED / LOCAL VERIFIED` | `ui_assets.py` получил workspace rail, policy/lineage, provider health, agents/workspaces, runtime telemetry и audit timeline; 237/237 tests после redesign; hidden side effects не добавлены |
| Observation/taint lineage | `IMPLEMENTED / LOCAL VERIFIED` | `resource_lineage.py`: append-only observations, sensitivity labels, stable idempotency, taint-aware egress deny и explicit approval; 3 focused tests |
| Documentation supply-chain safety | `IMPLEMENTED / CLEAN` | `docs_security_audit.py` scans Markdown fences; текущий tree: 0 high, 0 medium findings; policy: `docs/DOCUMENTATION_SECURITY_POLICY_RU.md` |
| Native packaging scaffolding | `PREPARED / NATIVE GATE BLOCKED` | `packaging/noesis_portable.spec`, `scripts/build_native.py`, `scripts/noesis_portable_entry.py`; dry-run correctly blocks Linux/CPython 3.12.3 for Windows/macOS Python 3.14 targets; no signing/elevation bypass |
| Cloudflare isolation integration | `INTERFACE REQUIRED / NOT CLAIMED` | Cloudflare Sandbox SDK is a TypeScript/Workers VM/container runtime, not a local Python dependency. NOESIS will integrate contracts/adapters and optional backend only after license, dependency and native isolation conformance review |

Current strategic differentiation target: observation-aware policy follows what the agent has seen; zero-access startup; explicit typed capabilities; recovery-first memory/workspaces; Cloudflare-style operator explainability; OpenCode-style Plan/Build/Explore/Review modes; Hermes-style persistent memory/skills/gateway reach; honest external benchmark evidence.

External sources: Cloudflare OS blog, Cloudflare Sandbox security model, Cloudflare Sandbox SDK, OpenCode agents/tools docs, PyInstaller operating mode/usage docs and Briefcase macOS docs are preserved in the competitive research note.

### Gateway and isolation implementation checkpoint

| Capability | Status | Boundary |
|---|---|---|
| Provider route registry | `IMPLEMENTED / TESTED` | Typed provider/model/capability pins; health snapshot is redacted and JSON-safe |
| External network gateway | `IMPLEMENTED / FAIL-CLOSED` | External route requires explicit approval; no injected transport means `not_run`; no hidden network call |
| Payload guard | `IMPLEMENTED / TESTED` | Bounded serialized request body; oversized payload is denied |
| Observation-aware egress | `IMPLEMENTED / TESTED` | Gateway consults observation ledger and denies tainted egress without approval |
| Cloudflare Sandbox integration | `ADAPTER ROADMAP` | Local code uses contracts and telemetry patterns; Cloudflare SDK remains optional TypeScript/Workers backend, not copied as a fake local VM |
| UI telemetry | `IMPLEMENTED / LOCAL VERIFIED` | Provider health, policy/lineage, runtime telemetry and audit timeline sections are present in the Cloudflare-style operator console |

Latest uncommitted gateway checkpoint is not release-ready until local/remote SHA are synchronized again.

### Competitive benchmark / native packaging / remote status

| Gate | Status | Evidence |
|---|---|---|
| Local benchmark | `PASS` | `docs/COMPETITIVE_BENCHMARK_RESULT_2026-08-17.md`; 10/10 contract cases, 240/240 full tests |
| External Hermes/OpenCode A/B | `NOT RUN` | Protocol prepared, but no external process substituted or simulated |
| Native packaging | `SCAFFOLD READY / NATIVE BLOCKED` | `scripts/build_native.py`, `packaging/noesis_portable.spec`, `docs/NATIVE_PACKAGING_RUNBOOK_RU.md`; Linux/3.12 fails closed for Windows/macOS/3.14 |
| Docs security | `PASS` | 0 high, 0 medium fenced-code findings |
| GitHub remote | `AUTH BLOCKED` | `gh auth status` and REST return invalid credentials / HTTP 401; local work may continue, remote publish waits for connector/CLI re-authentication |

### World-class differentiation checkpoint

| Bet | Status | Evidence |
|---|---|---|
| Measurable differentiation/anti-claims | `DOCUMENTED` | `docs/WORLD_CLASS_DIFFERENTIATION_BETS_RU_2026-08-17.md` defines metrics and forbids unsupported superiority claims |
| Context firewall | `IMPLEMENTED / LOCAL VERIFIED` | `noesis_harness/context_firewall.py`: sensitivity redaction, scope enforcement, bounded context, explicit approval; 3 focused tests |
| Provenance-aware memory | `IMPLEMENTED / LOCAL VERIFIED` | Observation ledger and taint-aware gateway egress are active primitives |
| Full current suite | `PASS` | 243/243 tests after context firewall |

### Execution assurance checkpoint

| Capability | Status | Evidence |
|---|---|---|
| Tamper-evident execution receipts | `IMPLEMENTED / LOCAL VERIFIED` | `noesis_harness/execution_assurance.py` hashes request, policy, workspace before/after, outcome, side effects and rollback availability |
| Receipt verification | `IMPLEMENTED / TESTED` | Tampering changes verification result; invalid outcomes fail closed |
| Recovery claim discipline | `DOCUMENTED` | Receipts record rollback availability but do not claim OS-level isolation or automatic recovery without backend evidence |
| Current local suite | `PASS` | 246/246 tests |

### Mandatory evidence gates: external A/B manifest

| Gate | Status | Evidence |
|---|---|---|
| Exact pinned runner protocol | `DEFINED` | `benchmarks/external_ab_manifest_v1.json` requires exact revisions before run |
| Same task fixtures | `DEFINED` | 6 fixed tasks: planning, exploration, coding, recovery, taint egress and multi-agent scope |
| Same budgets/permissions | `DEFINED` | 300s wall time, 20 steps, 32K context, 64K tool output, network deny-by-default |
| Evaluator metrics | `DEFINED` | Success, patch correctness, latency, cost, unauthorized egress, credential exposure, approval bypass, workspace escape, recovery and human review |
| Evidence rules | `FAIL-CLOSED` | `not_run` is not passed; unsupported is not zero failure; missing revision/seed digest blocks run |

### Python 3.14 / simulated A/B / hardened sandbox evidence

| Gate | Status | Note |
|---|---|---|
| Official CPython 3.14.7 Linux runtime | `PASS` | Source tarball SHA-256 verified; isolated runtime built under `runtime/python-3.14.7/` |
| NOESIS suite on 3.14.7 | `PASS` | 250/250 tests |
| Contract benchmark on 3.14.7 | `PASS` | 10/10 cases |
| Simulated external A/B | `SIMULATION ONLY` | NOESIS observed locally; Hermes/OpenCode explicitly `not_run` |
| Native build guard | `FAIL-CLOSED PASS` | 3.14 accepted; Linux correctly blocks Windows/macOS target packaging |
| Bubblewrap Linux backend | `PASS — LINUX SUBSET` | Network deny, host project path blocked, workspace-only write binding |
| Native Windows/macOS evidence | `NOT RUN` | Requires matching native hosts/runners |
| External Hermes/OpenCode execution | `NOT RUN` | Requires pinned runners, exact revisions and same model/provider |


## 2026-08-17 — reliability и packaging checkpoint

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-19 | SQLite lifecycle cleanup для Memory/Budget/Coordination/Graph/HITL/Queue | `DONE / LOCAL VERIFIED` | Все `with self._conn()` stores переведены на `_ManagedConnection`; Python 3.14 full suite больше не показывает SQLite connection warnings; оставшиеся 6 предупреждений относятся к cleanup HTTPError в `tempfile`, не к SQLite |
| DONE-20 | Chaos/recovery regression suite | `DONE / LOCAL VERIFIED` | `tests/test_chaos_recovery.py`: kill during write, interrupted provider response/requeue, corrupted receipt fail-closed, idempotent best-state recovery; 4/4 passed |
| DONE-21 | Full regression after reliability changes | `DONE / LOCAL VERIFIED` | Python 3.14.7: **254/254 passed**; `git diff --check` clean |
| DONE-22 | Static Windows/macOS native packaging manifests | `DONE / LOCAL VERIFIED` | `packaging/windows_manifest.json`, `packaging/macos_manifest.json`; explicit Python 3.14, target-host build, checksum and no-secret gates |
| DONE-23 | Native builder dry-run honesty gate | `DONE / LOCAL VERIFIED` | `scripts/build_native.py`: Python 3.14 gate passes; Linux host correctly returns target mismatch for Windows/macOS, therefore no false native artifact claim |

### Следующий execution order

1. Расширить локальный A/B evaluator метриками patch correctness, recovery, egress, credential leakage, approval bypass и human-review time.
2. Подготовить connector-neutral runner contract для Hermes/OpenCode; фактические external runs остаются `not_run` до pinned environments.
3. После появления Windows/macOS host evidence выполнить native build, startup/auth/shutdown smoke tests и SHA-256 artifact audit.
4. Удалить или отдельно классифицировать оставшиеся HTTPError `ResourceWarning` в тестовых сетевых fixtures; SQLite lifecycle warnings считать закрытыми.


## 2026-08-17 — reliability gate R-01 closure

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-24 | HTTPError lifecycle в тестовых HTTP fixtures | `DONE / LOCAL VERIFIED` | `test_control_plane_ui.py`, `test_gateway_fixture.py`, `test_health_auth.py`, `test_health_session_api.py` и `test_ui_contract_health.py` явно читают и закрывают ожидаемые HTTPError bodies |
| DONE-25 | HTTPError lifecycle в provider/bridge transports | `DONE / LOCAL VERIFIED` | `provider_invocation.py` и `bridge_discovery.py` закрывают HTTPError после bounded read; fail-soft status contract сохранён |
| DONE-26 | Полный reliability regression | `DONE / LOCAL VERIFIED` | Python 3.14.7: **254/254 passed**, `ResourceWarning` count: **0**, `git diff --check`: clean |

**Следующий активный gate:** перейти к phase 2 master-плана — расширить fault-injection coverage для interrupted provider response, corrupted receipt, rollback/session resume и kill-at-checkpoint; код, focused tests и этот checklist обновляются в одном execution cycle.


## 2026-08-17 — Phase 2 fault-injection checkpoint F-01

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-27 | Provider timeout boundary | `DONE / LOCAL VERIFIED` | Injected `TimeoutError` преобразуется в `ProviderInvocationError("provider_timeout")`; committed invocation result не создаётся |
| DONE-28 | Interrupted/partial provider response | `DONE / LOCAL VERIFIED` | Truncated JSON body fail-closed с `provider_invalid_json`; bounded response and side-effect contract сохранены |
| DONE-29 | Phase 2 regression after provider fault gate | `DONE / LOCAL VERIFIED` | Focused provider tests: **5/5 passed**; full Python 3.14.7 suite: **256/256 passed**; `ResourceWarning`: **0** |

Синхронный документ acceptance criteria: `docs/EVALUATION_PROTOCOL.md`, раздел `Phase 2 fault-injection gate — provider boundary`. Следующий незавершённый Phase 2 gate — расширить fault injection на session resume/rollback и повреждённое durable state, после чего перейти к native packaging evidence.


## 2026-08-17 — Phase 2 fault-injection checkpoint F-02

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-30 | Повреждённый durable Fiber checkpoint | `DONE / LOCAL VERIFIED` | `FiberStore` распознаёт malformed/non-object JSON как `FiberCorrupt`; runner не вызывается |
| DONE-31 | Quarantine повреждённого checkpoint | `DONE / LOCAL VERIFIED` | Запись переводится в `status='corrupted'`, `error='checkpoint_corrupt'`; `recoverable()` исключает её, другие fibers продолжают recovery |
| DONE-32 | Phase 2 resume/corruption regression | `DONE / LOCAL VERIFIED` | Fiber + chaos focused tests: **7/7 passed**; full Python 3.14.7 suite: **257/257 passed**; полный suite `ResourceWarning`: **0** |

Синхронный acceptance criteria добавлен в `docs/EVALUATION_PROTOCOL.md`, раздел `Phase 2 fault-injection gate — durable checkpoint corruption`. Следующий незавершённый Phase 2 gate — fault injection на session/task resume и rollback boundary; после завершения Phase 2 активируется packaging evidence gate.


## 2026-08-17 — Phase 2 fault-injection checkpoint F-03

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-33 | Session resume после interrupted JSONL append | `DONE / LOCAL VERIFIED` | Последний malformed tail автоматически обрезается; `TaskSessionStore.resume()` восстанавливает последний committed task state |
| DONE-34 | Rollback boundary после reopen | `DONE / LOCAL VERIFIED` | `review → rolled_back` сохраняется после reopen; повторный `rolled_back → planned` разрешён только с новым command ID |
| DONE-35 | Middle-line event corruption | `DONE / LOCAL VERIFIED` | `EventStoreCorrupt` fail-closed останавливает replay, malformed history не пропускается молча |
| DONE-36 | Phase 2 session/replay regression | `DONE / LOCAL VERIFIED` | Focused session/projection tests: **13/13 passed**; full Python 3.14.7 suite: **259/259 passed**; `ResourceWarning`: **0** |

Синхронные критерии добавлены в `docs/EVALUATION_PROTOCOL.md`, раздел `Phase 2 fault-injection gate — session resume and rollback boundary`. Phase 2 fault-injection gates завершены; следующий master gate — **Phase 3: Windows/macOS Python 3.14 packaging evidence**.


## 2026-08-17 — Phase 3 packaging checkpoint P-01

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-37 | Deterministic portable SHA-256 manifest | `DONE / LOCAL VERIFIED` | `build_portable_artifact.py` создаёт `PORTABLE_MANIFEST.json` с размером и SHA-256 каждого shipped file; `.env`, models, secrets и virtual environments исключаются |
| DONE-38 | SPDX file SBOM | `DONE / LOCAL VERIFIED` | Artifact содержит `PORTABLE_SBOM.spdx.json` в SPDX 2.3; SBOM file list и checksums совпадают с manifest |
| DONE-39 | Packaging evidence regression | `DONE / LOCAL VERIFIED` | Focused packaging tests: **10/10 passed**; real project artifact: **9,076 files**, SPDX 2.3, ZIP 264,521,172 bytes; full Python 3.14.7 suite: **261/261 passed**, `ResourceWarning`: **0** |
| DONE-40 | Windows/macOS manifest synchronization | `DONE / LOCAL VERIFIED` | `packaging/windows_manifest.json` и `packaging/macos_manifest.json` теперь требуют SHA-256 manifest и `PORTABLE_SBOM.spdx.json` |

Синхронный runbook: `docs/NATIVE_PACKAGING_RUNBOOK_RU.md`. Linux sandbox всё ещё не является доказательством native `.exe`/`.app`; следующий Phase 3 gate — target-host verification contract и signed/notarized artifact evidence path.


## 2026-08-17 — Phase 3 packaging checkpoint P-02

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-41 | Target-host native evidence verifier | `DONE / LOCAL VERIFIED` | Добавлен `scripts/verify_native_artifact.py`: Python 3.14/OS gate, `.exe`/`.app` shape, deterministic SHA-256 и platform signing checks; приложение не запускается |
| DONE-42 | Signed/notarized evidence policy | `DONE / LOCAL VERIFIED` | Windows требует Authenticode; macOS требует `codesign` и `spctl`; `development_unsigned` допускается только с явным флагом и не является release evidence |
| DONE-43 | Linux honesty gate | `DONE / LOCAL VERIFIED` | Linux при Windows/macOS target возвращает `not_run` + `target_host_or_python_mismatch`, без false native claim |
| DONE-44 | Native evidence regression | `DONE / LOCAL VERIFIED` | Focused native/packaging tests: **6/6 passed**; full Python 3.14.7 suite: **265/265 passed**; `ResourceWarning`: **0** |

Синхронный runbook: `docs/NATIVE_PACKAGING_RUNBOOK_RU.md`; синхронные manifests: `packaging/windows_manifest.json`, `packaging/macos_manifest.json`. Следующий Phase 3 gate — native CI/runbook smoke contract и artifact evidence schema audit; фактические Windows/macOS builds остаются `not_run` до target hosts.


## 2026-08-17 — Phase 3 packaging checkpoint P-03

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-45 | Static native packaging contract auditor | `DONE / LOCAL VERIFIED` | `scripts/verify_packaging_contract.py` проверяет Windows/macOS manifests, Python 3.14-only policy, verifier/SHA-256/SBOM/signature gates |
| DONE-46 | CI packaging-contract smoke job | `DONE / LOCAL VERIFIED` | `.github/workflows/ci.yml` добавлен job на Python 3.14: manifest audit, source artifact SBOM build и expected Linux native mismatch assertion |
| DONE-47 | Artifact evidence schema audit | `DONE / LOCAL VERIFIED` | Contract report: оба manifests `passed`, `native_builds_executed=false`, schema `noesis.packaging-contract.v1` |
| DONE-48 | Phase 3 contract regression | `DONE / LOCAL VERIFIED` | Focused packaging contract tests: **7/7 passed**; full Python 3.14.7 suite: **266/266 passed**; `ResourceWarning`: **0** |

Синхронный runbook: `docs/NATIVE_PACKAGING_RUNBOOK_RU.md`. Phase 3 native target-host evidence всё ещё `not_run`; CI contract не подменяет реальный Windows/macOS build, signing или notarization.


## 2026-08-17 — Phase 4 checkpoint A-01

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-49 | Expanded deterministic A/B metric schema | `DONE / LOCAL VERIFIED` | Evaluator теперь различает `observed` и `not_run` для task success, test pass rate, latency, patch correctness, context retention, budget, egress, credentials, approval bypass, workspace escape, recovery и human review/operator burden |
| DONE-50 | Connector-neutral pinned runner contract | `DONE / LOCAL VERIFIED` | Добавлен `scripts/external_runner_contract.py`: exact revision, task-manifest SHA-256, model/provider, argv array без shell interpolation, disposable workspace, no credentials и explicit status enum |
| DONE-51 | External result validation | `DONE / LOCAL VERIFIED` | `passed`, `failed`, `unsupported`, `not_run` принимаются явно; shared workspace и shell-string command fail-closed |
| DONE-52 | Phase 4 evaluator/runner regression | `DONE / LOCAL VERIFIED` | Focused tests: **8/8 passed**; simulated report содержит **13 metric records**; full Python 3.14.7 suite: **270/270 passed**; `ResourceWarning`: **0** |
| DONE-53 | Python 3.14 test fixture lifecycle hygiene | `DONE / LOCAL VERIFIED` | `tests/test_fibers.py` больше не полагается на SQLite context manager как на close; explicit `db.close()` устраняет allocation-traced warnings |

Синхронный runner policy: `docs/EXTERNAL_AB_RUNNER_REQUIREMENTS_RU_2026-08-17.md`. Hermes/OpenCode реальные execution lanes остаются `not_run` до pinned revisions/native runners; текущий report не выдаёт ranking.


## 2026-08-17 — Phase 4 checkpoint A-02

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-54 | Runner-result ingestion | `DONE / LOCAL VERIFIED` | `scripts/ingest_runner_result.py` проверяет spec/result identity: system, revision, task-manifest SHA-256, argv и workspace |
| DONE-55 | Signed evidence manifest | `DONE / LOCAL VERIFIED` | Создаётся `noesis.runner-evidence.v1` с HMAC-SHA256; runtime key не сохраняется в JSON; `verify_evidence()` ловит tampering |
| DONE-56 | Evidence security gates | `DONE / LOCAL VERIFIED` | Credential-like content, shared workspace, invalid metric status и identity mismatch fail-closed; `not_run` остаётся валидным явным статусом |
| DONE-57 | Phase 4 evidence regression | `DONE / LOCAL VERIFIED` | Focused tests: **8/8 passed**; full Python 3.14.7 suite: **274/274 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/EXTERNAL_AB_RUNNER_REQUIREMENTS_RU_2026-08-17.md`. HMAC envelope является operator integrity mechanism и не заявляется как публичная release signature. Hermes/OpenCode фактические evidence records всё ещё `not_run` до pinned execution.


## 2026-08-17 — Phase 4 checkpoint A-03

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-58 | Protocol fingerprint | `DONE / LOCAL VERIFIED` | Runner spec/evidence теперь содержит fingerprint из task-manifest SHA-256, model/provider и workspace policy |
| DONE-59 | Unified signed-evidence evaluator | `DONE / LOCAL VERIFIED` | `scripts/evaluate_signed_ab.py` принимает только accepted evidence с валидной HMAC-подписью |
| DONE-60 | Comparable-metric gate | `DONE / LOCAL VERIFIED` | При общем fingerprint numeric `observed` metrics могут сравниваться; при mismatch или tamper все metrics получают `comparable=false`, ranking не создаётся |
| DONE-61 | Phase 4 evaluation regression | `DONE / LOCAL VERIFIED` | Focused tests: **11/11 passed**; full Python 3.14.7 suite: **277/277 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/EXTERNAL_AB_RUNNER_REQUIREMENTS_RU_2026-08-17.md`. Фактические Hermes/OpenCode records всё ещё `not_run`; evaluator не создаёт сравнительный результат без pinned protocol fingerprint.


## 2026-08-17 — Phase 4 checkpoint A-04

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-62 | Reproducible local task fixture | `DONE / LOCAL VERIFIED` | `run_local_signed_ab_fixture.py` создаёт deterministic task-manifest и общий protocol fingerprint |
| DONE-63 | End-to-end evidence pipeline | `DONE / LOCAL VERIFIED` | Synthetic Hermes/OpenCode records проходят ingestion → HMAC verification → unified evaluator → JSON report artifact |
| DONE-64 | Local comparability proof | `DONE / LOCAL VERIFIED` | Два accepted signed records, `comparable=true`, **6 metric records**, `external_processes_started=false` |
| DONE-65 | Phase 4 fixture regression | `DONE / LOCAL VERIFIED` | Focused tests: **8/8 passed**; full Python 3.14.7 suite: **278/278 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/EXTERNAL_AB_RUNNER_REQUIREMENTS_RU_2026-08-17.md`. Этот lane доказывает только correctness plumbing/evidence pipeline; он не является реальным Hermes/OpenCode execution или quality ranking.


## 2026-08-17 — Phase 4 checkpoint A-05

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-66 | Connector-neutral execution adapter | `DONE / LOCAL VERIFIED` | `scripts/pinned_runner_adapter.py` принимает pinned spec и запускает только argv-массивом с `shell=False` |
| DONE-67 | Explicit approval gate | `DONE / LOCAL VERIFIED` | Без `approval=True` выполнение отклоняется; shared/credential-enabled workspace fail-closed |
| DONE-68 | Runtime containment contract | `DONE / LOCAL VERIFIED` | Требуется существующий disposable workspace; environment минимален; timeout и redacted stdout/stderr возвращаются структурированно |
| DONE-69 | Phase 4 adapter regression | `DONE / LOCAL VERIFIED` | Focused tests: **13/13 passed**; full Python 3.14.7 suite: **283/283 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/EXTERNAL_AB_RUNNER_REQUIREMENTS_RU_2026-08-17.md`. Adapter не запускается без явного approval и не превращает отсутствие Hermes/OpenCode configuration в `not_run`-подмену.


## 2026-08-17 — Phase 4 checkpoint A-06

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-70 | Dry-run operator bridge | `DONE / LOCAL VERIFIED` | `scripts/run_external_lane.py` создаёт plan `execution=not_started` без запуска процесса |
| DONE-71 | Approval bridge | `DONE / LOCAL VERIFIED` | `--execute` без `--approve` возвращает `denied/not_run`; запуск возможен только при явном approval |
| DONE-72 | Structured external outcome | `DONE / LOCAL VERIFIED` | Approved controlled fixture возвращает `started`, status, return code, timeout и redacted output |
| DONE-73 | Phase 4 lane regression | `DONE / LOCAL VERIFIED` | Focused tests: **12/12 passed**; full Python 3.14.7 suite: **286/286 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/EXTERNAL_AB_RUNNER_REQUIREMENTS_RU_2026-08-17.md`. Hermes/OpenCode остаются `not_run`, пока оператор не предоставит exact pinned configuration и явно не подтвердит execution.


## 2026-08-17 — Phase 4 checkpoint A-07

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-74 | Structured outcome → canonical result | `DONE / LOCAL VERIFIED` | `outcome_to_result()` превращает approved `started` outcome в observed task metric, а denied/not_started — в explicit `not_run` |
| DONE-75 | Evidence signing bridge | `DONE / LOCAL VERIFIED` | Converted result проходит существующий ingestion/HMAC verification contract |
| DONE-76 | Not-run comparison exclusion | `DONE / LOCAL VERIFIED` | Unified evaluator требует минимум два accepted signed non-`not_run` records и общий fingerprint; denied/not_run не сравниваются |
| DONE-77 | Phase 4 outcome regression | `DONE / LOCAL VERIFIED` | Focused tests: **12/12 passed**; full Python 3.14.7 suite: **288/288 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/EXTERNAL_AB_RUNNER_REQUIREMENTS_RU_2026-08-17.md`. Фактический Hermes/OpenCode execution остаётся `not_run` без exact pinned config и explicit approval.


## 2026-08-17 — Phase 4 checkpoint A-08 / closeout

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-78 | Local A/B release report | `DONE / LOCAL VERIFIED` | `noesis.local-ab-release.v1` содержит evaluation, provenance, evidence source digests и `external_processes_started=false` |
| DONE-79 | Hash-linked audit trail | `DONE / LOCAL VERIFIED` | Три audit events с sequence, `prev_hash` и `event_hash`; tampered payload fail-closed |
| DONE-80 | Report integrity | `DONE / LOCAL VERIFIED` | HMAC signature и `verify_report()` подтверждают целостность report; runtime key не сохраняется |
| DONE-81 | Phase 4 closeout regression | `DONE / LOCAL VERIFIED` | Focused report tests: **7/7 passed**; full Python 3.14.7 suite: **290/290 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/EXTERNAL_AB_RUNNER_REQUIREMENTS_RU_2026-08-17.md`. Phase 4 закрыт для локального evidence plumbing. Hermes/OpenCode фактический execution и ranking остаются `not_run` до pinned native/external environments и explicit approval. Следующий master gate — **Phase 5: Trust Plane и security holdouts**.


## 2026-08-18 — Phase 5 checkpoint T-01

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-82 | Child environment holdout | `DONE / LOCAL VERIFIED` | Неallowlisted environment key отклоняется до запуска child |
| DONE-83 | Symlink entrypoint holdout | `DONE / LOCAL VERIFIED` | Raw symlink проверяется до `resolve()`; ссылка на разрешённый файл не обходит workspace boundary |
| DONE-84 | Output budget holdout | `DONE / LOCAL VERIFIED` | stdout/stderr ограничены `output_limit`; превышение возвращает `output_budget_exceeded` |
| DONE-85 | Credential-like output holdout | `DONE / LOCAL VERIFIED` | Token-like output redacts to `[REDACTED_CREDENTIAL]` и возвращает `credential_like_output_blocked`; raw value не попадает в result |
| DONE-86 | Phase 5 child-runtime regression | `DONE / LOCAL VERIFIED` | Focused tests: **9/9 passed**; full Python 3.14.7 suite: **294/294 passed**; `ResourceWarning`: **0** |

Trust Plane boundary: child runtime остаётся process boundary, а не заявлением о полном OS sandbox; network без verified sandbox adapter по-прежнему fail-closed.


## 2026-08-18 — Phase 5 checkpoint T-02

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-87 | Mixed-scope Context Firewall holdout | `DONE / LOCAL VERIFIED` | Разрешённые items сохраняют порядок; restricted item redacted без explicit approval |
| DONE-88 | Provenance/resource IDs | `DONE / LOCAL VERIFIED` | `ContextDecision.included_resource_ids` сохраняет resource IDs включённых items в том же порядке |
| DONE-89 | Stable digest and budget | `DONE / LOCAL VERIFIED` | Повторный assembled text даёт одинаковый SHA-256 digest; `max_chars` не превышается |
| DONE-90 | Invalid scope fail-closed | `DONE / LOCAL VERIFIED` | Пустой allowed scope и item без scope отклоняются `ValueError` |
| DONE-91 | Phase 5 firewall regression | `DONE / LOCAL VERIFIED` | Focused tests: **6/6 passed**; full Python 3.14.7 suite: **297/297 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/TRUST_PLANE_SECURITY_HOLDOUTS_RU.md`. Следующий Trust Plane gate: resource lineage parent-chain и scope-confusion holdouts.


## 2026-08-18 — Phase 5 checkpoint T-03

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-92 | Parent identity validation | `DONE / LOCAL VERIFIED` | `parent_observation` должен существовать в той же session; неизвестный/cross-session parent отклоняется |
| DONE-93 | Sensitivity non-downgrade | `DONE / LOCAL VERIFIED` | Derived observation не может понизить sensitivity parent |
| DONE-94 | Cross-agent taint propagation | `DONE / LOCAL VERIFIED` | Derived sensitive resource другого agent блокирует egress без explicit approval |
| DONE-95 | Lineage holdout regression | `DONE / LOCAL VERIFIED` | Focused tests: **5/5 passed**; full Python 3.14.7 suite: **299/299 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/TRUST_PLANE_SECURITY_HOLDOUTS_RU.md`. Следующий Trust Plane gate: Gatekeeper audit redaction и approval/request scope-confusion holdouts.


## 2026-08-18 — Phase 5 checkpoint T-04

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-96 | Gatekeeper credential redaction | `DONE / LOCAL VERIFIED` | Nested token/bearer/provider patterns и sensitive argument keys не сохраняются в audit JSONL |
| DONE-97 | Request identity binding | `DONE / LOCAL VERIFIED` | Persisted `identity_digest` связывает request с session/task/agent/capability/action/target/side-effect |
| DONE-98 | Request scope-confusion holdout | `DONE / LOCAL VERIFIED` | Повторное использование explicit `request_id` в другой identity отклоняется `request_identity_conflict` |
| DONE-99 | Phase 5 Gatekeeper regression | `DONE / LOCAL VERIFIED` | Focused tests: **7/7 passed**; full Python 3.14.7 suite: **301/301 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/TRUST_PLANE_SECURITY_HOLDOUTS_RU.md`. Следующий Trust Plane gate: security corpus expansion и cross-component approval-bypass holdouts.


## 2026-08-18 — Phase 5 checkpoint T-05

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-100 | Security corpus expansion | `DONE / LOCAL VERIFIED` | Добавлены shell injection, path traversal и environment-secret holdouts; corpus расширен до **21 case** |
| DONE-101 | Gatekeeper cross-component scanner | `DONE / LOCAL VERIFIED` | Action/target сканируются до approval; findings возвращают `security_policy_denied` |
| DONE-102 | Safe argument handling | `DONE / LOCAL VERIFIED` | Arguments проходят redaction перед scanner serialization; credential values не блокируют безопасную audit redaction и не сохраняются |
| DONE-103 | Approval-bypass regression | `DONE / LOCAL VERIFIED` | Shell/path/env holdouts не достигают approval/commit transition |
| DONE-104 | Phase 5 security corpus regression | `DONE / LOCAL VERIFIED` | Focused tests: **11/11 passed**; full Python 3.14.7 suite: **302/302 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/TRUST_PLANE_SECURITY_HOLDOUTS_RU.md`. Следующий Trust Plane gate: cross-component end-to-end policy matrix для ContextFirewall → Gatekeeper → ChildExecutionRuntime.


## 2026-08-18 — Phase 5 checkpoint T-06

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-105 | TrustPlane orchestration boundary | `DONE / LOCAL VERIFIED` | Новый `noesis_harness/trust_plane.py` последовательно связывает Firewall → Lineage → Gatekeeper → Child Runtime |
| DONE-106 | Public-path matrix | `DONE / LOCAL VERIFIED` | Public context + read capability проходят все четыре слоя и завершаются `completed` |
| DONE-107 | Restricted-path matrix | `DONE / LOCAL VERIFIED` | Без approval restricted context останавливается на lineage и не достигает Gatekeeper/child |
| DONE-108 | Explicit-approval matrix | `DONE / LOCAL VERIFIED` | Approval включает restricted context, но child boundary и security gates остаются обязательными |
| DONE-109 | Cross-component regression | `DONE / LOCAL VERIFIED` | Focused tests: **4/4 passed**; full Python 3.14.7 suite: **306/306 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/TRUST_PLANE_SECURITY_HOLDOUTS_RU.md`. Следующий Trust Plane gate: audit/provenance event chain для end-to-end decision, включая denied/approved ordering и отсутствие raw restricted content.


## 2026-08-18 — Phase 5 checkpoint T-07

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-110 | Durable decision audit | `DONE / LOCAL VERIFIED` | TrustPlane пишет `noesis.trust-plane-decision.v1` для denied и approved paths |
| DONE-111 | Hash-linked ordering | `DONE / LOCAL VERIFIED` | Audit stream начинается zero hash и связывает каждый event через `prev_hash`/`event_hash` |
| DONE-112 | Raw restricted-content exclusion | `DONE / LOCAL VERIFIED` | В JSONL сохраняются только digest, IDs и reason/status metadata; raw context отсутствует |
| DONE-113 | Audit-chain regression | `DONE / LOCAL VERIFIED` | Focused tests: **5/5 passed**; full Python 3.14.7 suite: **307/307 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/TRUST_PLANE_SECURITY_HOLDOUTS_RU.md`. Следующий Trust Plane gate: audit tamper/replay recovery и cross-session decision provenance.


## 2026-08-18 — Phase 5 checkpoint T-08

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-114 | Interrupted audit tail recovery | `DONE / LOCAL VERIFIED` | Reopen ремонтирует malformed final JSONL tail без потери валидного decision |
| DONE-115 | Middle corruption fail-closed | `DONE / LOCAL VERIFIED` | Corruption до последующих events вызывает `EventStoreCorrupt`; replay не пропускает историю |
| DONE-116 | Cross-session decision provenance | `DONE / LOCAL VERIFIED` | Audit events сохраняют session/task/agent identity и hash-linked ordering |
| DONE-117 | Phase 5 audit recovery regression | `DONE / LOCAL VERIFIED` | Focused tests: **7/7 passed**; full Python 3.14.7 suite: **309/309 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/TRUST_PLANE_SECURITY_HOLDOUTS_RU.md`. Trust Plane и Phase 5 closeout локально завершены; следующий high-leverage gate: `docs/NEXT_HIGH_LEVERAGE_GATE_RU.md` — cross-platform task-execution parity с native sandbox, task/session path и pinned external evidence.


## 2026-08-18 — Phase 5 FINAL CLOSEOUT

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-118 | Security holdout closeout audit | `DONE / LOCAL VERIFIED` | `docs/PHASE5_SECURITY_CLOSEOUT_RU.md` |
| DONE-119 | Machine-readable evidence manifest | `DONE / LOCAL VERIFIED` | `docs/PHASE5_SECURITY_CLOSEOUT_EVIDENCE.json` |
| DONE-120 | Focused Trust Plane/security regression | `DONE / LOCAL VERIFIED` | **38/38 passed** on CPython 3.14.7 |
| DONE-121 | Full regression and warning hygiene | `DONE / LOCAL VERIFIED` | **309/309 passed**, `ResourceWarning: 0` |
| DONE-122 | Git/diff integrity closeout | `DONE / LOCAL VERIFIED` | `git diff --check` passed; working tree clean at audit |

### Phase 5 boundary

Phase 5 закрыт только как локально проверенный Private Release Candidate. Реальные pinned Hermes/OpenCode runs, native Windows/macOS builds, Authenticode/codesign/notarization и публичная release signature остаются `NOT RUN`. Заявление «лучший в мире» до этих external evidence gates запрещено.

Следующий приоритет мастер-плана: **Phase 6 External Evidence** — pinned runner execution against Hermes/OpenCode, signed evidence ingestion, reproducible A/B metrics and target-host native artifact evidence.


## 2026-08-18 — Phase 6 External Evidence boundary

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| P6-01 | Зафиксировать NOESIS/Hermes/OpenCode architectural boundary | `DONE / LOCAL VERIFIED` | Hermes/OpenCode — только black-box baselines; core NOESIS самостоятельный и не зависит от их runtime |
| P6-02 | Зафиксировать reproducible external A/B manifest | `DONE / LOCAL VERIFIED` | `benchmarks/external_ab_manifest_v1.json`; exact revision, same-model policy, disposable workspace, deny-by-default network |
| P6-03 | Проверить connector-neutral runner plumbing | `DONE / LOCAL VERIFIED` | **7/7** external contract tests; dry-run, approval gate, shell-safe argv, structured outcomes |
| P6-04 | Проверить synthetic evaluator plumbing | `DONE / LOCAL VERIFIED` | NOESIS local contract lane **10/10** + local safety metrics **5/5 observed passed**; credential holdout **21/21**; synthetic-only, ranking запрещён; `docs/PARALLEL_LOCAL_SAFETY_EVIDENCE.json` SHA-256 `85d4bf58070399f749d7f422b785f104bffbc78d661e83f4d52e1127a1c2f4b4` |
| P6-05 | Реальный pinned Hermes/OpenCode execution | `BLOCKED / EXTERNAL ENV REQUIRED` | `not_run`; exact revisions, disposable runners и operator-approved environments ещё не предоставлены |
| P6-06 | Comparative quality report | `BLOCKED / DEPENDS ON P6-05` | Не строить ranking до signed evidence всех трёх систем |

Синхронный протокол: `docs/PHASE6_EXTERNAL_EVIDENCE_PROTOCOL_RU.md`. Формулировка статуса: **NOESIS имеет подготовленный и локально проверенный external benchmark plumbing; превосходство над Hermes/OpenCode пока не доказано**.


## 2026-08-18 — Phase 6 pinned lane operations

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| P6-07 | Operator runbook для pinned lanes | `DONE / LOCAL VERIFIED` | `docs/PHASE6_PINNED_LANE_RUNBOOK_RU.md`: generate → validate → explicit execute → signed ingestion |
| P6-08 | Placeholder/false-evidence prevention | `DONE / LOCAL VERIFIED` | Exact revision, manifest SHA-256, disposable workspace и HMAC key обязательны; strict execution/status combinations и 64-hex digest validation fail closed; placeholders не принимаются как evidence |
| P6-09 | Реальный запуск lanes | `BLOCKED / EXTERNAL ENV REQUIRED` | Hermes/OpenCode exact revisions и disposable operator environments отсутствуют; статус остаётся `not_run` |

Операторский runbook не включает Hermes/OpenCode в NOESIS core. Он нужен только для независимых reproducible baseline runs.


## 2026-08-18 — Phase 6 dry-run smoke verification

| Проверка | Результат |
|---|---|
| NOESIS pinned plan | `PASS`: `execution=not_started`, approval required |
| Hermes pinned plan template | `PASS`: `execution=not_started`, approval required |
| OpenCode pinned plan template | `PASS`: `execution=not_started`, approval required |
| Execute without `--approve` | `PASS`: `execution=denied`, `status=not_run` |
| Process safety | Во время smoke verification ни один external process не запускался |

Это только control-plane smoke verification с локальными dry-run revisions и не является external A/B evidence.


## 2026-08-18 — Safe parallel multi-agent execution

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| MA-01 | Bounded parallel orchestration layer | `DONE / LOCAL VERIFIED` | `noesis_harness/parallel_agent.py`; concurrency cap 1…8, fail-isolated results |
| MA-02 | Per-agent workspace isolation | `DONE / LOCAL VERIFIED` | Unique child directories, traversal and symlink checks |
| MA-03 | Capability and approval gate | `DONE / LOCAL VERIFIED` | Safe capability allowlist; credentials/cross-agent/shared-workspace/shell/inline-code deny; writes require approval |
| MA-04 | Provenance-bearing lane context | `DONE / LOCAL VERIFIED` | `session_id`, `task_id`, `agent_id`, workspace and capabilities are immutable context fields |
| MA-05 | Focused parallel security tests | `DONE / LOCAL VERIFIED` | `tests/test_parallel_agent.py`: **8/8 passed** on Python 3.14.7; coordination integration **19/19** |
| MA-06 | OS boundary honesty | `DONE / DOCUMENTED` | `docs/MULTI_AGENT_EXECUTION_SECURITY_RU.md`; scheduler is not an OS sandbox; executable tools/skills remain behind ChildExecutionRuntime |

Full regression после lease integration: **317/317 passed**, `ResourceWarning: 0`. Следующий шаг: интеграция parallel orchestration с durable action/task ledger и recovery coordinator без обхода Trust Plane.


## 2026-08-18 — Durable action recovery integration

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| MA-07 | Owner-only action requeue | `DONE / LOCAL VERIFIED` | `Actions.requeue(aid, agent)` возвращает только текущий active owner в pending |
| MA-08 | Lease-aware parallel execution | `DONE / LOCAL VERIFIED` | Held task получает `blocked` без callback; свободная task выполняется и lease освобождается |
| MA-09 | Parallel/recovery regression | `DONE / LOCAL VERIFIED` | Focused **20/20 passed**; full Python 3.14.7 suite **318/318 passed**, `ResourceWarning: 0` |

Безопасная граница сохраняется: parallel scheduler не выполняет model-generated code и не заменяет OS sandbox; executable tools/skills идут через ChildExecutionRuntime.


## 2026-08-18 — Durable Actions/RecoveryCoordinator integration

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| MA-10 | Actions-aware parallel lifecycle | `DONE / LOCAL VERIFIED` | Lane claim → callback → `done`; exception → owner-only `pending`; foreign active action не запускается |
| MA-11 | RecoveryCoordinator action requeue | `DONE / LOCAL VERIFIED` | Optional Actions store, explicit `action_id`/`action_owner`, `requeued_actions` в `DurableRecoveryReport` |
| MA-12 | Durable recovery regression | `DONE / LOCAL VERIFIED` | Focused parallel/coordination/recovery **25/25 passed** |
| MA-13 | Full regression after integration | `DONE / LOCAL VERIFIED` | Python 3.14.7: **321/321 passed**, `ResourceWarning: 0`, `git diff --check` passed |

Граница Trust Plane сохранена: callback orchestration не выполняет model-generated code; executable tools/skills остаются за ChildExecutionRuntime, а best-state/fiber/work recovery не обходятся Actions requeue.


## 2026-08-18 — Versioned session/task command API и streaming

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| API-01 | Versioned command envelope | `DONE / LOCAL VERIFIED` | `schema_version=noesis.task-session.v1`, bounded `command_id`, 4 allowlisted commands |
| API-02 | Durable command dispatch | `DONE / LOCAL VERIFIED` | session/task create, task transition и session message через existing EventStore/state machine |
| API-03 | Idempotent create retry | `DONE / LOCAL VERIFIED` | Deterministic IDs from command_id; повторная команда не создаёт duplicate event/object |
| API-04 | Task read/resume routes | `DONE / LOCAL VERIFIED` | `GET /api/tasks/<id>`, existing session resume и task state validation |
| API-05 | Interactive bounded stream | `DONE / LOCAL VERIFIED` | Command events в `SessionEventBuffer`, monotonic sequence, Last-Event-ID SSE replay, 64 KiB event bound |
| API-06 | Security/default boundary | `DONE / LOCAL VERIFIED` | Mutation opt-in only; default server read-only; redaction/no raw credentials; loopback/auth defaults preserved |
| API-07 | Command API regression | `DONE / LOCAL VERIFIED` | Focused **16/16 passed**; full Python 3.14.7 suite **326/326 passed**, `ResourceWarning: 0` |

Синхронный contract: `docs/TASK_SESSION_COMMAND_API_V1_RU.md`. API не запускает модели/tools/skills; side effects требуют отдельного Trust Plane/Gatekeeper/ChildExecutionRuntime path.


## 2026-08-18 — Command-to-execution bridge

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| EXEC-01 | `task.request_execution` command | `DONE / LOCAL VERIFIED` | Только переводит task в `waiting_approval`; непосредственный execution не запускается |
| EXEC-02 | TaskExecutionBridge | `DONE / LOCAL VERIFIED` | `noesis_harness/execution_bridge.py`; session match, explicit approval и waiting-state gates |
| EXEC-03 | Actions/parallel lifecycle mapping | `DONE / LOCAL VERIFIED` | Claim → callback → done/requeue; task → review/failed |
| EXEC-04 | Execution event sink | `DONE / LOCAL VERIFIED` | Metadata-only lane/task events для bounded SSE; raw output/workspace не публикуются |
| EXEC-05 | Bridge security/recovery tests | `DONE / LOCAL VERIFIED` | Focused **30/30 passed**; full Python 3.14.7 suite **329/329 passed**, `ResourceWarning: 0` |

Синхронный contract: `docs/TASK_EXECUTION_BRIDGE_RU.md`. Bridge не является model runner и не обходит Trust Plane/ChildExecutionRuntime.


## 2026-08-18 — Safe parallel release-readiness lanes

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| REL-01 | Bounded parallel packaging contract lane | `DONE / LOCAL VERIFIED` | Static Windows/macOS manifests passed; `native_builds_executed=false` |
| REL-02 | Native target honesty lane | `DONE / LOCAL VERIFIED` | Windows/macOS verifier вернул `not_run: target_host_or_python_mismatch` на Linux; native claim не создан |
| REL-03 | Command contract lane | `DONE / LOCAL VERIFIED` | Versioned `task.request_execution` оставил task в `waiting_approval`; execution без approval не начался |
| REL-04 | Execution bridge lane | `DONE / LOCAL VERIFIED` | Actions claim → SafeParallelExecutor → action `done` → task `review`; metadata provenance events |
| REL-05 | Parallel safety evidence | `DONE / LOCAL VERIFIED` | **4/4 passed**, 4 уникальные workspaces, network=false, credentials=false, model-generated code=false |
| REL-06 | Machine-readable lane evidence | `DONE / LOCAL VERIFIED` | `docs/PARALLEL_RELEASE_LANES_EVIDENCE.json`; SHA-256 `a72bd2057b62fe3e89af3a92c12a1097b189dc98e212aa8f39b12289258fe0e4` |

Синхронный summary: `docs/PARALLEL_RELEASE_LANES_RU.md`. Этот результат подтверждает локальный release-readiness plumbing, но не native `.exe`/`.app`, Authenticode/codesign/notarization или external A/B superiority.


## 2026-08-18 — Native artifact evidence hardening

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| NAT-01 | Portable manifest/SBOM verifier | `DONE / LOCAL VERIFIED` | `scripts/verify_portable_artifact.py`; archive coverage, sizes, SHA-256 и SPDX-2.3 checksum equality |
| NAT-02 | Portable tamper/coverage negative matrix | `DONE / LOCAL VERIFIED` | Valid pass, tampered payload SHA fail, unexpected file coverage fail, missing metadata fail |
| NAT-03 | Parallel native evidence lanes | `DONE / LOCAL VERIFIED` | 4/4 lanes: portable SHA/SBOM, static manifests, Python 3.14 identity, native target matrix |
| NAT-04 | Native target honesty | `DONE / LOCAL VERIFIED` | Windows/macOS on Linux: `not_run`, `target_host_or_python_mismatch`; native claim не создаётся |
| NAT-05 | Evidence report validation | `DONE / LOCAL VERIFIED` | `scripts/validate_parallel_native_evidence_report.py`: PASS; evidence SHA-256 `d48f8807229e9d6c5ffcd872dcecfcf87b56b2b3f6038392a9b46bc31f6f0d79` |
| NAT-06 | Native evidence documentation | `DONE / DOCUMENTED` | `docs/PARALLEL_NATIVE_EVIDENCE_RU.md` и `docs/PARALLEL_NATIVE_EVIDENCE.json` |

Current boundary: static/native evidence plumbing verified locally; real Windows `.exe`, macOS `.app`, Authenticode, codesign и notarization требуют target hosts и остаются external gates.


## 2026-08-18 — Native build dry-run и signing policy matrix

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| NAT-07 | Windows/macOS build dry-run gates | `DONE / LOCAL VERIFIED` | 2 lanes passed; `dry_run=true`, `run_permitted=false`, target mismatch блокирует backend |
| NAT-08 | No-subprocess target mismatch test | `DONE / LOCAL VERIFIED` | Windows/macOS `--run` при Linux host: exit `2`, patched `subprocess.run` не вызван |
| NAT-09 | Signing-policy matrix | `DONE / LOCAL VERIFIED` | Authenticode/codesign/notarization requirements обнаружены; `native_builds_executed=false` |
| NAT-10 | Parallel build-policy evidence | `DONE / LOCAL VERIFIED` | 4/4 lanes passed; CPython 3.14.7; unique workspaces; no network/credentials/model code |
| NAT-11 | Machine-readable evidence | `DONE / LOCAL VERIFIED` | `docs/PARALLEL_BUILD_POLICY_EVIDENCE.json`; SHA-256 `9bbf15a92226c6ee15c53c569afefba7094910362a33d5a250848aa85554f18a` |

Summary: `docs/PARALLEL_BUILD_POLICY_EVIDENCE_RU.md`. Native Windows/macOS build и signing evidence остаются external host gates.


## 2026-08-18 — CI и packaging runbook consistency

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| CI-01 | CI Python 3.14 runtime gate | `DONE / LOCAL VERIFIED` | Workflow запускает `verify_python314.py --json` |
| CI-02 | CI portable artifact verification | `DONE / LOCAL VERIFIED` | Workflow строит ZIP и запускает `verify_portable_artifact.py` |
| CI-03 | Dual target honesty gate | `DONE / LOCAL VERIFIED` | Workflow проверяет Windows и macOS `target_host_or_python_mismatch` с exit `2` |
| CI-04 | Runbook consistency checker | `DONE / LOCAL VERIFIED` | CI/runbook markers: `missing=[]` |
| CI-05 | Parallel CI consistency lanes | `DONE / LOCAL VERIFIED` | **4/4 passed**, 4 unique workspaces, no network/credentials/model code |
| CI-06 | Machine-readable evidence | `DONE / LOCAL VERIFIED` | `docs/PARALLEL_CI_CONSISTENCY_EVIDENCE.json`; SHA-256 `884dd1a55ab5deba55174276d83a45c160b822679ec083eff26d44855cb0ebb8` |

Синхронный summary: `docs/PARALLEL_CI_CONSISTENCY_RU.md`. Native target builds и signatures всё ещё требуют Windows/macOS hosts.


## 2026-08-18 — Offline release audit

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| AUD-01 | Offline secret/AST audit | `DONE / LOCAL VERIFIED` | Zero credential-like hits, zero syntax errors, zero actual `eval`/`exec` calls |
| AUD-02 | Package export audit | `DONE / LOCAL VERIFIED` | Governance/execution exports доступны; 8 проверенных names |
| AUD-03 | Git integrity audit | `DONE / LOCAL VERIFIED` | `git diff --check` gate; final clean-tree requirement |
| AUD-04 | Russian checklist audit | `DONE / LOCAL VERIFIED` | MA/API/EXEC/REL/NAT/CI markers присутствуют |
| AUD-05 | Offline audit boundary | `DONE / LOCAL VERIFIED` | `remote_parity_checked=false`; `git ls-remote` не вызывается без explicit `--remote` |
| AUD-06 | Parallel audit evidence | `DONE / RUN AFTER CLEAN CHECKPOINT` | 4 SafeParallelExecutor lanes, unique workspaces, no network/credentials/model code |

Summary: `docs/PARALLEL_RELEASE_AUDIT_RU.md`. Remote Git parity, native target builds и external A/B остаются отдельными explicit gates.


### AUD-06 evidence result

Offline release audit на committed checkpoint завершён: **4/4 lanes passed**, secret hits `0`, syntax errors `0`, AST `eval/exec` calls `0`, package exports `8/8`, `git diff --check=true`, `working_tree_clean=true`, unique workspaces `4`, `remote_parity_checked=false`. Machine-readable evidence: `docs/PARALLEL_RELEASE_AUDIT_EVIDENCE.json`; SHA-256 `462b32364cfe9f4d34017c26278f9d81626c73b93d1172879a57c2437a45b944`.


## 2026-08-18 — Release metadata, licensing и provenance coverage

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| META-01 | Required release metadata files | `DONE / LOCAL VERIFIED` | LICENSE, README, CHANGELOG, THIRD_PARTY_NOTICES, pyproject, docs index и provenance manifest: 7/7 |
| META-02 | Python/license/private-release alignment | `DONE / LOCAL VERIFIED` | 9/9 metadata checks passed; Python 3.14, MIT, private GitHub и owner-approved public gate согласованы |
| META-03 | Third-party provenance parity | `DONE / LOCAL VERIFIED` | 5 upstreams; NOTICE↔JSON parity; `code_copied=false`, `runtime_dependency=false` |
| META-04 | CHANGELOG/docs navigation freshness | `DONE / LOCAL VERIFIED` | Unreleased 2026-08-18 snapshot, new evidence docs linked, missing markers `[]` |
| META-05 | Parallel metadata/SBOM evidence | `DONE / LOCAL VERIFIED` | 4/4 lanes passed; 4 unique workspaces; no network/credentials/model code; file `docs/PARALLEL_METADATA_EVIDENCE.json`; evidence SHA-256 `34cf5bfa3f74e909f041600e9dd147d2400711a90e68d5dc1290772ceeca0608` |

Summary: `docs/PARALLEL_METADATA_EVIDENCE_RU.md`. Metadata/provenance coverage закрыта локально; license review при будущем vendoring и external/native gates остаются отдельными задачами.


## Progress snapshot после metadata/provenance audit — 2026-08-18

По уникальным checklist IDs: **234/243 = 96,30%** имеют `DONE`, `PASS`, `VERIFIED`, `IMPLEMENTED`, `PREPARED` или эквивалентный локально закрытый статус. **9/243 = 3,70%** остаются открытыми: 5 external environment/evidence gates (`P6-05`, `P6-06`, `P6-09`, `P12-01`, `P13-01`) и 4 owner decisions (`P4-03`, `USER-03`, `USER-04`, `USER-05`). Этот процент отражает checklist coverage, а не доказанность superiority claim: native target evidence и external A/B всё ещё обязательны.


## 2026-08-18 — Documentation security и link/schema audit

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DOC-01 | Markdown fence security audit | `DONE / LOCAL VERIFIED` | 0 high и 0 medium findings по docs Markdown |
| DOC-02 | Local relative-link audit | `DONE / LOCAL VERIFIED` | 77 Markdown files, 39 local links, missing targets `0`; generated runtime docs исключены |
| DOC-03 | JSON evidence/schema coverage | `DONE / LOCAL VERIFIED` | 17 selected JSON files, valid JSON и `schema_version` coverage, findings `0` |
| DOC-04 | Russian checklist/evidence navigation | `DONE / LOCAL VERIFIED` | Required markers и evidence paths присутствуют |
| DOC-05 | Parallel documentation evidence | `DONE / LOCAL VERIFIED` | 4/4 lanes passed; 4 unique workspaces; no network/credentials/model code; file `docs/PARALLEL_DOCUMENTATION_EVIDENCE.json`; SHA-256 `9670271eb713b0538886395651e03321f65d453ee9b75cf5b11bddc017ce79bd` |

Summary: `docs/PARALLEL_DOCUMENTATION_EVIDENCE_RU.md`.
