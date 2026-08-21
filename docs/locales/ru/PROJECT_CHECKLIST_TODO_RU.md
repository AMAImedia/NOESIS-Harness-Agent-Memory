# NOESIS — совместный checklist и TODO

Дата контрольного состояния: **2026-08-18**

Репозиторий: `AMAImedia/NOESIS-Harness-Agent-Memory`

Режим публикации: **Private**

Текущая ветка: `main`

Последний подтверждённый remote commit: `3555f4d` — `Bind governed learning lifecycle in portable runtime`

Текущий рабочий этап: **Gate 3 child runtime в работе; manifest/grant contract и Linux/Bubblewrap filesystem/network adversarial isolation локально verified; native/external gates остаются blocked/not_run**

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
| P4-03 | Optional Electron/Tauri wrapper decision | Владелец + агент | `DECISION MEMO READY / WAITING FOR USER` | Recommendation: keep stdlib-first control plane as canonical baseline; defer wrapper; if native shell is required, prefer isolated optional Tauri layer after native CI and IPC/security review; Electron not default; memo `docs/locales/ru/DECISION_MEMO_P4-03_DESKTOP_WRAPPER_2026-08-17_RU.md` |
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
| P13-01 | Comparative A/B and task benchmarks | Агент | `CONTRACT PROTOCOL + LOCAL BASELINE READY / EXTERNAL A-B NOT RUN` | `docs/locales/ru/COMPETITIVE_BENCHMARK_PROTOCOL_RU.md` defines fixed task suite, metrics, stop conditions and reporting schema. `docs/TASK_EXECUTION_PARITY_EVIDENCE.json` records local-only parity `passed`; `scripts/pinned_lane_orchestrator.py` and `docs/PINNED_EXTERNAL_LANE_MATRIX_EVIDENCE.json` prepare connector-neutral Hermes/OpenCode/DeepSeek Harness lanes; external runs and native Windows/macOS measurements remain explicitly `not_run`. |

| DOC-06 | English-primary / Russian-supplemental policy | `DONE / LOCAL VERIFIED` | `docs/LANGUAGE_POLICY.md`; code-facing scope contains no unintended Cyrillic, Russian documents use the `_RU.md` suffix, and stable evidence status values remain English. |

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

Подробный memo: `docs/locales/ru/RELEASE_READINESS_AUDIT_2026-08-17_RU.md`. Visibility не изменялась; branch protection, native runner verification, wrapper choice и public release остаются решениями владельца.

## 4. Как устроена документация проекта

Чтобы не потеряться среди документов, используется не один огромный файл, а короткая иерархия с одним индексом:

| Уровень | Файл | Назначение |
|---|---|---|
| 1 | `docs/locales/ru/PROJECT_CHECKLIST_TODO_RU.md` | Главный operational checklist: что делать сейчас, кто отвечает и какое доказательство нужно |
| 2 | `docs/README.md` | Навигационный индекс всех документов |
| 3 | `docs/locales/ru/PLAN_NOESIS_1.0_MASTER_RU.md` | Архитектурные фазы и долгосрочные gates |
| 4 | `docs/PORTABLE_UI_INTEGRATION_ROADMAP.md` | Отдельный план Portable Control Plane и Hermes/DeepSeek adapters |
| `docs/UI_CONTRACT_V1.md` | Точная versioned схема envelope, `/health`, `/models`, errors и redaction |
| 5 | `docs/ARCHITECTURE_1.0_NEXTGEN.md` и `docs/locales/ru/EVALUATION_PROTOCOL_RU.md` | Детали архитектуры и измерений |
| 6 | `docs/locales/ru/IMPLEMENTATION_REPORT_2026-08_RU.md` и `docs/RELEASE_READINESS_AUDIT_2026-08.md` | Фактические результаты, commits, tests и release gates |
| 7 | `docs/locales/ru/GITHUB_FREE_PRIVATE_LIMITS_AND_NEXT_TASKS_2026-08-17_RU.md` | Ограничения GitHub Free/private и порядок задач, не зависящих от платных функций |
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
| Cloudflare/OpenCode/Hermes research | `RESEARCHED / ROADMAP UPDATED` | Сохранены официальные findings и источники в `docs/COMPETITIVE_RESEARCH_CLOUDFLARE_OPENCODE_HERMES_2026-08-17.md`; стратегический roadmap — `docs/locales/ru/STRATEGIC_ROADMAP_BEYOND_COMPETITORS_2026-08-17_RU.md` |
| Cloudflare-style operator UI | `IMPLEMENTED / LOCAL VERIFIED` | `ui_assets.py` получил workspace rail, policy/lineage, provider health, agents/workspaces, runtime telemetry и audit timeline; 237/237 tests после redesign; hidden side effects не добавлены |
| Observation/taint lineage | `IMPLEMENTED / LOCAL VERIFIED` | `resource_lineage.py`: append-only observations, sensitivity labels, stable idempotency, taint-aware egress deny и explicit approval; 3 focused tests |
| Documentation supply-chain safety | `IMPLEMENTED / CLEAN` | `docs_security_audit.py` scans Markdown fences; текущий tree: 0 high, 0 medium findings; policy: `docs/locales/ru/DOCUMENTATION_SECURITY_POLICY_RU.md` |
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
| Native packaging | `SCAFFOLD READY / NATIVE BLOCKED` | `scripts/build_native.py`, `packaging/noesis_portable.spec`, `docs/locales/ru/NATIVE_PACKAGING_RUNBOOK_RU.md`; Linux/3.12 fails closed for Windows/macOS/3.14 |
| Docs security | `PASS` | 0 high, 0 medium fenced-code findings |
| GitHub remote | `AUTH BLOCKED` | `gh auth status` and REST return invalid credentials / HTTP 401; local work may continue, remote publish waits for connector/CLI re-authentication |

### World-class differentiation checkpoint

| Bet | Status | Evidence |
|---|---|---|
| Measurable differentiation/anti-claims | `DOCUMENTED` | `docs/locales/ru/WORLD_CLASS_DIFFERENTIATION_BETS_2026-08-17_RU.md` defines metrics and forbids unsupported superiority claims |
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

Синхронный документ acceptance criteria: `docs/locales/ru/EVALUATION_PROTOCOL_RU.md`, раздел `Phase 2 fault-injection gate — provider boundary`. Следующий незавершённый Phase 2 gate — расширить fault injection на session resume/rollback и повреждённое durable state, после чего перейти к native packaging evidence.


## 2026-08-17 — Phase 2 fault-injection checkpoint F-02

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-30 | Повреждённый durable Fiber checkpoint | `DONE / LOCAL VERIFIED` | `FiberStore` распознаёт malformed/non-object JSON как `FiberCorrupt`; runner не вызывается |
| DONE-31 | Quarantine повреждённого checkpoint | `DONE / LOCAL VERIFIED` | Запись переводится в `status='corrupted'`, `error='checkpoint_corrupt'`; `recoverable()` исключает её, другие fibers продолжают recovery |
| DONE-32 | Phase 2 resume/corruption regression | `DONE / LOCAL VERIFIED` | Fiber + chaos focused tests: **7/7 passed**; full Python 3.14.7 suite: **257/257 passed**; полный suite `ResourceWarning`: **0** |

Синхронный acceptance criteria добавлен в `docs/locales/ru/EVALUATION_PROTOCOL_RU.md`, раздел `Phase 2 fault-injection gate — durable checkpoint corruption`. Следующий незавершённый Phase 2 gate — fault injection на session/task resume и rollback boundary; после завершения Phase 2 активируется packaging evidence gate.


## 2026-08-17 — Phase 2 fault-injection checkpoint F-03

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-33 | Session resume после interrupted JSONL append | `DONE / LOCAL VERIFIED` | Последний malformed tail автоматически обрезается; `TaskSessionStore.resume()` восстанавливает последний committed task state |
| DONE-34 | Rollback boundary после reopen | `DONE / LOCAL VERIFIED` | `review → rolled_back` сохраняется после reopen; повторный `rolled_back → planned` разрешён только с новым command ID |
| DONE-35 | Middle-line event corruption | `DONE / LOCAL VERIFIED` | `EventStoreCorrupt` fail-closed останавливает replay, malformed history не пропускается молча |
| DONE-36 | Phase 2 session/replay regression | `DONE / LOCAL VERIFIED` | Focused session/projection tests: **13/13 passed**; full Python 3.14.7 suite: **259/259 passed**; `ResourceWarning`: **0** |

Синхронные критерии добавлены в `docs/locales/ru/EVALUATION_PROTOCOL_RU.md`, раздел `Phase 2 fault-injection gate — session resume and rollback boundary`. Phase 2 fault-injection gates завершены; следующий master gate — **Phase 3: Windows/macOS Python 3.14 packaging evidence**.


## 2026-08-17 — Phase 3 packaging checkpoint P-01

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-37 | Deterministic portable SHA-256 manifest | `DONE / LOCAL VERIFIED` | `build_portable_artifact.py` создаёт `PORTABLE_MANIFEST.json` с размером и SHA-256 каждого shipped file; `.env`, models, secrets и virtual environments исключаются |
| DONE-38 | SPDX file SBOM | `DONE / LOCAL VERIFIED` | Artifact содержит `PORTABLE_SBOM.spdx.json` в SPDX 2.3; SBOM file list и checksums совпадают с manifest |
| DONE-39 | Packaging evidence regression | `DONE / LOCAL VERIFIED` | Focused packaging tests: **10/10 passed**; real project artifact: **9,076 files**, SPDX 2.3, ZIP 264,521,172 bytes; full Python 3.14.7 suite: **261/261 passed**, `ResourceWarning`: **0** |
| DONE-40 | Windows/macOS manifest synchronization | `DONE / LOCAL VERIFIED` | `packaging/windows_manifest.json` и `packaging/macos_manifest.json` теперь требуют SHA-256 manifest и `PORTABLE_SBOM.spdx.json` |

Синхронный runbook: `docs/locales/ru/NATIVE_PACKAGING_RUNBOOK_RU.md`. Linux sandbox всё ещё не является доказательством native `.exe`/`.app`; следующий Phase 3 gate — target-host verification contract и signed/notarized artifact evidence path.


## 2026-08-17 — Phase 3 packaging checkpoint P-02

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-41 | Target-host native evidence verifier | `DONE / LOCAL VERIFIED` | Добавлен `scripts/verify_native_artifact.py`: Python 3.14/OS gate, `.exe`/`.app` shape, deterministic SHA-256 и platform signing checks; приложение не запускается |
| DONE-42 | Signed/notarized evidence policy | `DONE / LOCAL VERIFIED` | Windows требует Authenticode; macOS требует `codesign` и `spctl`; `development_unsigned` допускается только с явным флагом и не является release evidence |
| DONE-43 | Linux honesty gate | `DONE / LOCAL VERIFIED` | Linux при Windows/macOS target возвращает `not_run` + `target_host_or_python_mismatch`, без false native claim |
| DONE-44 | Native evidence regression | `DONE / LOCAL VERIFIED` | Focused native/packaging tests: **6/6 passed**; full Python 3.14.7 suite: **265/265 passed**; `ResourceWarning`: **0** |

Синхронный runbook: `docs/locales/ru/NATIVE_PACKAGING_RUNBOOK_RU.md`; синхронные manifests: `packaging/windows_manifest.json`, `packaging/macos_manifest.json`. Следующий Phase 3 gate — native CI/runbook smoke contract и artifact evidence schema audit; фактические Windows/macOS builds остаются `not_run` до target hosts.


## 2026-08-17 — Phase 3 packaging checkpoint P-03

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-45 | Static native packaging contract auditor | `DONE / LOCAL VERIFIED` | `scripts/verify_packaging_contract.py` проверяет Windows/macOS manifests, Python 3.14-only policy, verifier/SHA-256/SBOM/signature gates |
| DONE-46 | CI packaging-contract smoke job | `DONE / LOCAL VERIFIED` | `.github/workflows/ci.yml` добавлен job на Python 3.14: manifest audit, source artifact SBOM build и expected Linux native mismatch assertion |
| DONE-47 | Artifact evidence schema audit | `DONE / LOCAL VERIFIED` | Contract report: оба manifests `passed`, `native_builds_executed=false`, schema `noesis.packaging-contract.v1` |
| DONE-48 | Phase 3 contract regression | `DONE / LOCAL VERIFIED` | Focused packaging contract tests: **7/7 passed**; full Python 3.14.7 suite: **266/266 passed**; `ResourceWarning`: **0** |

Синхронный runbook: `docs/locales/ru/NATIVE_PACKAGING_RUNBOOK_RU.md`. Phase 3 native target-host evidence всё ещё `not_run`; CI contract не подменяет реальный Windows/macOS build, signing или notarization.


## 2026-08-17 — Phase 4 checkpoint A-01

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-49 | Expanded deterministic A/B metric schema | `DONE / LOCAL VERIFIED` | Evaluator теперь различает `observed` и `not_run` для task success, test pass rate, latency, patch correctness, context retention, budget, egress, credentials, approval bypass, workspace escape, recovery и human review/operator burden |
| DONE-50 | Connector-neutral pinned runner contract | `DONE / LOCAL VERIFIED` | Добавлен `scripts/external_runner_contract.py`: exact revision, task-manifest SHA-256, model/provider, argv array без shell interpolation, disposable workspace, no credentials и explicit status enum |
| DONE-51 | External result validation | `DONE / LOCAL VERIFIED` | `passed`, `failed`, `unsupported`, `not_run` принимаются явно; shared workspace и shell-string command fail-closed |
| DONE-52 | Phase 4 evaluator/runner regression | `DONE / LOCAL VERIFIED` | Focused tests: **8/8 passed**; simulated report содержит **13 metric records**; full Python 3.14.7 suite: **270/270 passed**; `ResourceWarning`: **0** |
| DONE-53 | Python 3.14 test fixture lifecycle hygiene | `DONE / LOCAL VERIFIED` | `tests/test_fibers.py` больше не полагается на SQLite context manager как на close; explicit `db.close()` устраняет allocation-traced warnings |

Синхронный runner policy: `docs/locales/ru/EXTERNAL_AB_RUNNER_REQUIREMENTS_2026-08-17_RU.md`. Hermes/OpenCode реальные execution lanes остаются `not_run` до pinned revisions/native runners; текущий report не выдаёт ranking.


## 2026-08-17 — Phase 4 checkpoint A-02

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-54 | Runner-result ingestion | `DONE / LOCAL VERIFIED` | `scripts/ingest_runner_result.py` проверяет spec/result identity: system, revision, task-manifest SHA-256, argv и workspace |
| DONE-55 | Signed evidence manifest | `DONE / LOCAL VERIFIED` | Создаётся `noesis.runner-evidence.v1` с HMAC-SHA256; runtime key не сохраняется в JSON; `verify_evidence()` ловит tampering |
| DONE-56 | Evidence security gates | `DONE / LOCAL VERIFIED` | Credential-like content, shared workspace, invalid metric status и identity mismatch fail-closed; `not_run` остаётся валидным явным статусом |
| DONE-57 | Phase 4 evidence regression | `DONE / LOCAL VERIFIED` | Focused tests: **8/8 passed**; full Python 3.14.7 suite: **274/274 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/locales/ru/EXTERNAL_AB_RUNNER_REQUIREMENTS_2026-08-17_RU.md`. HMAC envelope является operator integrity mechanism и не заявляется как публичная release signature. Hermes/OpenCode фактические evidence records всё ещё `not_run` до pinned execution.


## 2026-08-17 — Phase 4 checkpoint A-03

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-58 | Protocol fingerprint | `DONE / LOCAL VERIFIED` | Runner spec/evidence теперь содержит fingerprint из task-manifest SHA-256, model/provider и workspace policy |
| DONE-59 | Unified signed-evidence evaluator | `DONE / LOCAL VERIFIED` | `scripts/evaluate_signed_ab.py` принимает только accepted evidence с валидной HMAC-подписью |
| DONE-60 | Comparable-metric gate | `DONE / LOCAL VERIFIED` | При общем fingerprint numeric `observed` metrics могут сравниваться; при mismatch или tamper все metrics получают `comparable=false`, ranking не создаётся |
| DONE-61 | Phase 4 evaluation regression | `DONE / LOCAL VERIFIED` | Focused tests: **11/11 passed**; full Python 3.14.7 suite: **277/277 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/locales/ru/EXTERNAL_AB_RUNNER_REQUIREMENTS_2026-08-17_RU.md`. Фактические Hermes/OpenCode records всё ещё `not_run`; evaluator не создаёт сравнительный результат без pinned protocol fingerprint.


## 2026-08-17 — Phase 4 checkpoint A-04

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-62 | Reproducible local task fixture | `DONE / LOCAL VERIFIED` | `run_local_signed_ab_fixture.py` создаёт deterministic task-manifest и общий protocol fingerprint |
| DONE-63 | End-to-end evidence pipeline | `DONE / LOCAL VERIFIED` | Synthetic Hermes/OpenCode records проходят ingestion → HMAC verification → unified evaluator → JSON report artifact |
| DONE-64 | Local comparability proof | `DONE / LOCAL VERIFIED` | Два accepted signed records, `comparable=true`, **6 metric records**, `external_processes_started=false` |
| DONE-65 | Phase 4 fixture regression | `DONE / LOCAL VERIFIED` | Focused tests: **8/8 passed**; full Python 3.14.7 suite: **278/278 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/locales/ru/EXTERNAL_AB_RUNNER_REQUIREMENTS_2026-08-17_RU.md`. Этот lane доказывает только correctness plumbing/evidence pipeline; он не является реальным Hermes/OpenCode execution или quality ranking.


## 2026-08-17 — Phase 4 checkpoint A-05

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-66 | Connector-neutral execution adapter | `DONE / LOCAL VERIFIED` | `scripts/pinned_runner_adapter.py` принимает pinned spec и запускает только argv-массивом с `shell=False` |
| DONE-67 | Explicit approval gate | `DONE / LOCAL VERIFIED` | Без `approval=True` выполнение отклоняется; shared/credential-enabled workspace fail-closed |
| DONE-68 | Runtime containment contract | `DONE / LOCAL VERIFIED` | Требуется существующий disposable workspace; environment минимален; timeout и redacted stdout/stderr возвращаются структурированно |
| DONE-69 | Phase 4 adapter regression | `DONE / LOCAL VERIFIED` | Focused tests: **13/13 passed**; full Python 3.14.7 suite: **283/283 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/locales/ru/EXTERNAL_AB_RUNNER_REQUIREMENTS_2026-08-17_RU.md`. Adapter не запускается без явного approval и не превращает отсутствие Hermes/OpenCode configuration в `not_run`-подмену.


## 2026-08-17 — Phase 4 checkpoint A-06

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-70 | Dry-run operator bridge | `DONE / LOCAL VERIFIED` | `scripts/run_external_lane.py` создаёт plan `execution=not_started` без запуска процесса |
| DONE-71 | Approval bridge | `DONE / LOCAL VERIFIED` | `--execute` без `--approve` возвращает `denied/not_run`; запуск возможен только при явном approval |
| DONE-72 | Structured external outcome | `DONE / LOCAL VERIFIED` | Approved controlled fixture возвращает `started`, status, return code, timeout и redacted output |
| DONE-73 | Phase 4 lane regression | `DONE / LOCAL VERIFIED` | Focused tests: **12/12 passed**; full Python 3.14.7 suite: **286/286 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/locales/ru/EXTERNAL_AB_RUNNER_REQUIREMENTS_2026-08-17_RU.md`. Hermes/OpenCode остаются `not_run`, пока оператор не предоставит exact pinned configuration и явно не подтвердит execution.


## 2026-08-17 — Phase 4 checkpoint A-07

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-74 | Structured outcome → canonical result | `DONE / LOCAL VERIFIED` | `outcome_to_result()` превращает approved `started` outcome в observed task metric, а denied/not_started — в explicit `not_run` |
| DONE-75 | Evidence signing bridge | `DONE / LOCAL VERIFIED` | Converted result проходит существующий ingestion/HMAC verification contract |
| DONE-76 | Not-run comparison exclusion | `DONE / LOCAL VERIFIED` | Unified evaluator требует минимум два accepted signed non-`not_run` records и общий fingerprint; denied/not_run не сравниваются |
| DONE-77 | Phase 4 outcome regression | `DONE / LOCAL VERIFIED` | Focused tests: **12/12 passed**; full Python 3.14.7 suite: **288/288 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/locales/ru/EXTERNAL_AB_RUNNER_REQUIREMENTS_2026-08-17_RU.md`. Фактический Hermes/OpenCode execution остаётся `not_run` без exact pinned config и explicit approval.


## 2026-08-17 — Phase 4 checkpoint A-08 / closeout

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-78 | Local A/B release report | `DONE / LOCAL VERIFIED` | `noesis.local-ab-release.v1` содержит evaluation, provenance, evidence source digests и `external_processes_started=false` |
| DONE-79 | Hash-linked audit trail | `DONE / LOCAL VERIFIED` | Три audit events с sequence, `prev_hash` и `event_hash`; tampered payload fail-closed |
| DONE-80 | Report integrity | `DONE / LOCAL VERIFIED` | HMAC signature и `verify_report()` подтверждают целостность report; runtime key не сохраняется |
| DONE-81 | Phase 4 closeout regression | `DONE / LOCAL VERIFIED` | Focused report tests: **7/7 passed**; full Python 3.14.7 suite: **290/290 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/locales/ru/EXTERNAL_AB_RUNNER_REQUIREMENTS_2026-08-17_RU.md`. Phase 4 закрыт для локального evidence plumbing. Hermes/OpenCode фактический execution и ranking остаются `not_run` до pinned native/external environments и explicit approval. Следующий master gate — **Phase 5: Trust Plane и security holdouts**.


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

Синхронный документ: `docs/locales/ru/TRUST_PLANE_SECURITY_HOLDOUTS_RU.md`. Следующий Trust Plane gate: resource lineage parent-chain и scope-confusion holdouts.


## 2026-08-18 — Phase 5 checkpoint T-03

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-92 | Parent identity validation | `DONE / LOCAL VERIFIED` | `parent_observation` должен существовать в той же session; неизвестный/cross-session parent отклоняется |
| DONE-93 | Sensitivity non-downgrade | `DONE / LOCAL VERIFIED` | Derived observation не может понизить sensitivity parent |
| DONE-94 | Cross-agent taint propagation | `DONE / LOCAL VERIFIED` | Derived sensitive resource другого agent блокирует egress без explicit approval |
| DONE-95 | Lineage holdout regression | `DONE / LOCAL VERIFIED` | Focused tests: **5/5 passed**; full Python 3.14.7 suite: **299/299 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/locales/ru/TRUST_PLANE_SECURITY_HOLDOUTS_RU.md`. Следующий Trust Plane gate: Gatekeeper audit redaction и approval/request scope-confusion holdouts.


## 2026-08-18 — Phase 5 checkpoint T-04

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-96 | Gatekeeper credential redaction | `DONE / LOCAL VERIFIED` | Nested token/bearer/provider patterns и sensitive argument keys не сохраняются в audit JSONL |
| DONE-97 | Request identity binding | `DONE / LOCAL VERIFIED` | Persisted `identity_digest` связывает request с session/task/agent/capability/action/target/side-effect |
| DONE-98 | Request scope-confusion holdout | `DONE / LOCAL VERIFIED` | Повторное использование explicit `request_id` в другой identity отклоняется `request_identity_conflict` |
| DONE-99 | Phase 5 Gatekeeper regression | `DONE / LOCAL VERIFIED` | Focused tests: **7/7 passed**; full Python 3.14.7 suite: **301/301 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/locales/ru/TRUST_PLANE_SECURITY_HOLDOUTS_RU.md`. Следующий Trust Plane gate: security corpus expansion и cross-component approval-bypass holdouts.


## 2026-08-18 — Phase 5 checkpoint T-05

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-100 | Security corpus expansion | `DONE / LOCAL VERIFIED` | Добавлены shell injection, path traversal и environment-secret holdouts; corpus расширен до **21 case** |
| DONE-101 | Gatekeeper cross-component scanner | `DONE / LOCAL VERIFIED` | Action/target сканируются до approval; findings возвращают `security_policy_denied` |
| DONE-102 | Safe argument handling | `DONE / LOCAL VERIFIED` | Arguments проходят redaction перед scanner serialization; credential values не блокируют безопасную audit redaction и не сохраняются |
| DONE-103 | Approval-bypass regression | `DONE / LOCAL VERIFIED` | Shell/path/env holdouts не достигают approval/commit transition |
| DONE-104 | Phase 5 security corpus regression | `DONE / LOCAL VERIFIED` | Focused tests: **11/11 passed**; full Python 3.14.7 suite: **302/302 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/locales/ru/TRUST_PLANE_SECURITY_HOLDOUTS_RU.md`. Следующий Trust Plane gate: cross-component end-to-end policy matrix для ContextFirewall → Gatekeeper → ChildExecutionRuntime.


## 2026-08-18 — Phase 5 checkpoint T-06

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-105 | TrustPlane orchestration boundary | `DONE / LOCAL VERIFIED` | Новый `noesis_harness/trust_plane.py` последовательно связывает Firewall → Lineage → Gatekeeper → Child Runtime |
| DONE-106 | Public-path matrix | `DONE / LOCAL VERIFIED` | Public context + read capability проходят все четыре слоя и завершаются `completed` |
| DONE-107 | Restricted-path matrix | `DONE / LOCAL VERIFIED` | Без approval restricted context останавливается на lineage и не достигает Gatekeeper/child |
| DONE-108 | Explicit-approval matrix | `DONE / LOCAL VERIFIED` | Approval включает restricted context, но child boundary и security gates остаются обязательными |
| DONE-109 | Cross-component regression | `DONE / LOCAL VERIFIED` | Focused tests: **4/4 passed**; full Python 3.14.7 suite: **306/306 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/locales/ru/TRUST_PLANE_SECURITY_HOLDOUTS_RU.md`. Следующий Trust Plane gate: audit/provenance event chain для end-to-end decision, включая denied/approved ordering и отсутствие raw restricted content.


## 2026-08-18 — Phase 5 checkpoint T-07

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-110 | Durable decision audit | `DONE / LOCAL VERIFIED` | TrustPlane пишет `noesis.trust-plane-decision.v1` для denied и approved paths |
| DONE-111 | Hash-linked ordering | `DONE / LOCAL VERIFIED` | Audit stream начинается zero hash и связывает каждый event через `prev_hash`/`event_hash` |
| DONE-112 | Raw restricted-content exclusion | `DONE / LOCAL VERIFIED` | В JSONL сохраняются только digest, IDs и reason/status metadata; raw context отсутствует |
| DONE-113 | Audit-chain regression | `DONE / LOCAL VERIFIED` | Focused tests: **5/5 passed**; full Python 3.14.7 suite: **307/307 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/locales/ru/TRUST_PLANE_SECURITY_HOLDOUTS_RU.md`. Следующий Trust Plane gate: audit tamper/replay recovery и cross-session decision provenance.


## 2026-08-18 — Phase 5 checkpoint T-08

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-114 | Interrupted audit tail recovery | `DONE / LOCAL VERIFIED` | Reopen ремонтирует malformed final JSONL tail без потери валидного decision |
| DONE-115 | Middle corruption fail-closed | `DONE / LOCAL VERIFIED` | Corruption до последующих events вызывает `EventStoreCorrupt`; replay не пропускает историю |
| DONE-116 | Cross-session decision provenance | `DONE / LOCAL VERIFIED` | Audit events сохраняют session/task/agent identity и hash-linked ordering |
| DONE-117 | Phase 5 audit recovery regression | `DONE / LOCAL VERIFIED` | Focused tests: **7/7 passed**; full Python 3.14.7 suite: **309/309 passed**; `ResourceWarning`: **0** |

Синхронный документ: `docs/locales/ru/TRUST_PLANE_SECURITY_HOLDOUTS_RU.md`. Trust Plane и Phase 5 closeout локально завершены; следующий high-leverage gate: `docs/locales/ru/NEXT_HIGH_LEVERAGE_GATE_RU.md` — cross-platform task-execution parity с native sandbox, task/session path и pinned external evidence.


## 2026-08-18 — Phase 5 FINAL CLOSEOUT

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DONE-118 | Security holdout closeout audit | `DONE / LOCAL VERIFIED` | `docs/locales/ru/PHASE5_SECURITY_CLOSEOUT_RU.md` |
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

Синхронный протокол: `docs/locales/ru/PHASE6_EXTERNAL_EVIDENCE_PROTOCOL_RU.md`. Формулировка статуса: **NOESIS имеет подготовленный и локально проверенный external benchmark plumbing; превосходство над Hermes/OpenCode пока не доказано**.


## 2026-08-18 — Phase 6 pinned lane operations

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| P6-07 | Operator runbook для pinned lanes | `DONE / LOCAL VERIFIED` | `docs/locales/ru/PHASE6_PINNED_LANE_RUNBOOK_RU.md`: generate → validate → explicit execute → signed ingestion |
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
| MA-06 | OS boundary honesty | `DONE / DOCUMENTED` | `docs/locales/ru/MULTI_AGENT_EXECUTION_SECURITY_RU.md`; scheduler is not an OS sandbox; executable tools/skills remain behind ChildExecutionRuntime |

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

Синхронный contract: `docs/locales/ru/TASK_SESSION_COMMAND_API_V1_RU.md`. API не запускает модели/tools/skills; side effects требуют отдельного Trust Plane/Gatekeeper/ChildExecutionRuntime path.


## 2026-08-18 — Command-to-execution bridge

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| EXEC-01 | `task.request_execution` command | `DONE / LOCAL VERIFIED` | Только переводит task в `waiting_approval`; непосредственный execution не запускается |
| EXEC-02 | TaskExecutionBridge | `DONE / LOCAL VERIFIED` | `noesis_harness/execution_bridge.py`; session match, explicit approval и waiting-state gates |
| EXEC-03 | Actions/parallel lifecycle mapping | `DONE / LOCAL VERIFIED` | Claim → callback → done/requeue; task → review/failed |
| EXEC-04 | Execution event sink | `DONE / LOCAL VERIFIED` | Metadata-only lane/task events для bounded SSE; raw output/workspace не публикуются |
| EXEC-05 | Bridge security/recovery tests | `DONE / LOCAL VERIFIED` | Focused **30/30 passed**; full Python 3.14.7 suite **329/329 passed**, `ResourceWarning: 0` |

Синхронный contract: `docs/locales/ru/TASK_EXECUTION_BRIDGE_RU.md`. Bridge не является model runner и не обходит Trust Plane/ChildExecutionRuntime.


## 2026-08-18 — Safe parallel release-readiness lanes

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| REL-01 | Bounded parallel packaging contract lane | `DONE / LOCAL VERIFIED` | Static Windows/macOS manifests passed; `native_builds_executed=false` |
| REL-02 | Native target honesty lane | `DONE / LOCAL VERIFIED` | Windows/macOS verifier вернул `not_run: target_host_or_python_mismatch` на Linux; native claim не создан |
| REL-03 | Command contract lane | `DONE / LOCAL VERIFIED` | Versioned `task.request_execution` оставил task в `waiting_approval`; execution без approval не начался |
| REL-04 | Execution bridge lane | `DONE / LOCAL VERIFIED` | Actions claim → SafeParallelExecutor → action `done` → task `review`; metadata provenance events |
| REL-05 | Parallel safety evidence | `DONE / LOCAL VERIFIED` | **4/4 passed**, 4 уникальные workspaces, network=false, credentials=false, model-generated code=false |
| REL-06 | Machine-readable lane evidence | `DONE / LOCAL VERIFIED` | `docs/PARALLEL_RELEASE_LANES_EVIDENCE.json`; SHA-256 `a72bd2057b62fe3e89af3a92c12a1097b189dc98e212aa8f39b12289258fe0e4` |

Синхронный summary: `docs/locales/ru/PARALLEL_RELEASE_LANES_RU.md`. Этот результат подтверждает локальный release-readiness plumbing, но не native `.exe`/`.app`, Authenticode/codesign/notarization или external A/B superiority.


## 2026-08-18 — Native artifact evidence hardening

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| NAT-01 | Portable manifest/SBOM verifier | `DONE / LOCAL VERIFIED` | `scripts/verify_portable_artifact.py`; archive coverage, sizes, SHA-256 и SPDX-2.3 checksum equality |
| NAT-02 | Portable tamper/coverage negative matrix | `DONE / LOCAL VERIFIED` | Valid pass, tampered payload SHA fail, unexpected file coverage fail, missing metadata fail |
| NAT-03 | Parallel native evidence lanes | `DONE / LOCAL VERIFIED` | 4/4 lanes: portable SHA/SBOM, static manifests, Python 3.14 identity, native target matrix |
| NAT-04 | Native target honesty | `DONE / LOCAL VERIFIED` | Windows/macOS on Linux: `not_run`, `target_host_or_python_mismatch`; native claim не создаётся |
| NAT-05 | Evidence report validation | `DONE / LOCAL VERIFIED` | `scripts/validate_parallel_native_evidence_report.py`: PASS; evidence SHA-256 `d48f8807229e9d6c5ffcd872dcecfcf87b56b2b3f6038392a9b46bc31f6f0d79` |
| NAT-06 | Native evidence documentation | `DONE / DOCUMENTED` | `docs/locales/ru/PARALLEL_NATIVE_EVIDENCE_RU.md` и `docs/PARALLEL_NATIVE_EVIDENCE.json` |

Current boundary: static/native evidence plumbing verified locally; real Windows `.exe`, macOS `.app`, Authenticode, codesign и notarization требуют target hosts и остаются external gates.


## 2026-08-18 — Native build dry-run и signing policy matrix

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| NAT-07 | Windows/macOS build dry-run gates | `DONE / LOCAL VERIFIED` | 2 lanes passed; `dry_run=true`, `run_permitted=false`, target mismatch блокирует backend |
| NAT-08 | No-subprocess target mismatch test | `DONE / LOCAL VERIFIED` | Windows/macOS `--run` при Linux host: exit `2`, patched `subprocess.run` не вызван |
| NAT-09 | Signing-policy matrix | `DONE / LOCAL VERIFIED` | Authenticode/codesign/notarization requirements обнаружены; `native_builds_executed=false` |
| NAT-10 | Parallel build-policy evidence | `DONE / LOCAL VERIFIED` | 4/4 lanes passed; CPython 3.14.7; unique workspaces; no network/credentials/model code |
| NAT-11 | Machine-readable evidence | `DONE / LOCAL VERIFIED` | `docs/PARALLEL_BUILD_POLICY_EVIDENCE.json`; SHA-256 `9bbf15a92226c6ee15c53c569afefba7094910362a33d5a250848aa85554f18a` |

Summary: `docs/locales/ru/PARALLEL_BUILD_POLICY_EVIDENCE_RU.md`. Native Windows/macOS build и signing evidence остаются external host gates.


## 2026-08-18 — CI и packaging runbook consistency

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| CI-01 | CI Python 3.14 runtime gate | `DONE / LOCAL VERIFIED` | Workflow запускает `verify_python314.py --json` |
| CI-02 | CI portable artifact verification | `DONE / LOCAL VERIFIED` | Workflow строит ZIP и запускает `verify_portable_artifact.py` |
| CI-03 | Dual target honesty gate | `DONE / LOCAL VERIFIED` | Workflow проверяет Windows и macOS `target_host_or_python_mismatch` с exit `2` |
| CI-04 | Runbook consistency checker | `DONE / LOCAL VERIFIED` | CI/runbook markers: `missing=[]` |
| CI-05 | Parallel CI consistency lanes | `DONE / LOCAL VERIFIED` | **4/4 passed**, 4 unique workspaces, no network/credentials/model code |
| CI-06 | Machine-readable evidence | `DONE / LOCAL VERIFIED` | `docs/PARALLEL_CI_CONSISTENCY_EVIDENCE.json`; SHA-256 `884dd1a55ab5deba55174276d83a45c160b822679ec083eff26d44855cb0ebb8` |

Синхронный summary: `docs/locales/ru/PARALLEL_CI_CONSISTENCY_RU.md`. Native target builds и signatures всё ещё требуют Windows/macOS hosts.


## 2026-08-18 — Offline release audit

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| AUD-01 | Offline secret/AST audit | `DONE / LOCAL VERIFIED` | Zero credential-like hits, zero syntax errors, zero actual `eval`/`exec` calls |
| AUD-02 | Package export audit | `DONE / LOCAL VERIFIED` | Governance/execution exports доступны; 8 проверенных names |
| AUD-03 | Git integrity audit | `DONE / LOCAL VERIFIED` | `git diff --check` gate; final clean-tree requirement |
| AUD-04 | Russian checklist audit | `DONE / LOCAL VERIFIED` | MA/API/EXEC/REL/NAT/CI markers присутствуют |
| AUD-05 | Offline audit boundary | `DONE / LOCAL VERIFIED` | `remote_parity_checked=false`; `git ls-remote` не вызывается без explicit `--remote` |
| AUD-06 | Parallel audit evidence | `DONE / RUN AFTER CLEAN CHECKPOINT` | 4 SafeParallelExecutor lanes, unique workspaces, no network/credentials/model code |

Summary: `docs/locales/ru/PARALLEL_RELEASE_AUDIT_RU.md`. Remote Git parity, native target builds и external A/B остаются отдельными explicit gates.


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

Summary: `docs/locales/ru/PARALLEL_METADATA_EVIDENCE_RU.md`. Metadata/provenance coverage закрыта локально; license review при будущем vendoring и external/native gates остаются отдельными задачами.


## Progress snapshot после metadata/provenance audit — 2026-08-18

Progress snapshot: historical checklist coverage is retained below, but the normative remaining work is now defined by `docs/PLAN_NOESIS_1.0_MASTER.md`. The current next local gate is `NEXT-01` production learning lifecycle binding. Native Windows/macOS evidence and Hermes/OpenCode/DeepSeek Harness A/B remain `not_run` or `blocked`; no percentage is treated as proof of superiority.


## 2026-08-18 — Documentation security и link/schema audit

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| DOC-01 | Markdown fence security audit | `DONE / LOCAL VERIFIED` | 0 high и 0 medium findings по docs Markdown |
| DOC-02 | Local relative-link audit | `DONE / LOCAL VERIFIED` | 77 Markdown files, 39 local links, missing targets `0`; generated runtime docs исключены |
| DOC-03 | JSON evidence/schema coverage | `DONE / LOCAL VERIFIED` | 17 selected JSON files, valid JSON и `schema_version` coverage, findings `0` |
| DOC-04 | Russian checklist/evidence navigation | `DONE / LOCAL VERIFIED` | Required markers и evidence paths присутствуют |
| DOC-05 | Parallel documentation evidence | `DONE / LOCAL VERIFIED` | 4/4 lanes passed; 4 unique workspaces; no network/credentials/model code; file `docs/PARALLEL_DOCUMENTATION_EVIDENCE.json`; SHA-256 `9670271eb713b0538886395651e03321f65d453ee9b75cf5b11bddc017ce79bd` |

Summary: `docs/locales/ru/PARALLEL_DOCUMENTATION_EVIDENCE_RU.md`.

## 2026-08-18 — Signed evidence fail-closed gate

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| EVID-01 | Hostile-input verification для signed evidence | `DONE / LOCAL VERIFIED` | `verify_evidence()` возвращает `False` для malformed envelope, missing fields, invalid hashes/signatures, non-empty errors, rejected records и invalid keys; не выбрасывает исключение |
| EVID-02 | Regression coverage | `DONE / LOCAL VERIFIED` | `tests/test_runner_evidence.py`; полный Python 3.14 suite: `373/373 passed`, `ResourceWarning=0` |
| EVID-03 | Signed fixture evaluation | `DONE / LOCAL VERIFIED / SIMULATION ONLY` | Local fixture evaluator создал accepted Hermes/OpenCode records с matching fingerprint; `external_processes_started=false`; это не native/external A/B evidence |
| EVID-04 | English primary documentation | `DONE / LOCAL VERIFIED` | `docs/SIGNED_EVIDENCE_FAIL_CLOSED.md` и Russian localization `docs/locales/ru/SIGNED_EVIDENCE_FAIL_CLOSED_RU.md`; evidence status values остаются English |

Граница сохраняется: реальные Hermes/OpenCode/DeepSeek Harness execution, native macOS/Windows runs и superiority ranking требуют exact revisions, matching environments, disposable workspaces и explicit operator approval.

## 2026-08-18 — Documentation locale structure and stale-reference audit

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| LOC-01 | Перенос русской документации | `DONE / LOCAL VERIFIED` | 38 русских документов перенесены из `docs/` в `docs/locales/ru/`; root `docs/` оставлен для English primary layer |
| LOC-02 | Обновление code-facing paths | `DONE / LOCAL VERIFIED` | CI packaging consistency checker и test fixtures используют `docs/locales/ru/NATIVE_PACKAGING_RUNBOOK_RU.md`; stale root path устранён |
| LOC-03 | Duplicate/stale translation audit | `DONE / LOCAL VERIFIED` | `docs/LOCALIZATION_DUPLICATE_AUDIT.md`; exact duplicate hashes `0`, stale root references `0`, primary-layer Cyrillic findings `0` |
| LOC-04 | Markdown link conformance | `DONE / LOCAL VERIFIED` | 90 Markdown files, 61 local links, missing targets `0` |

Нормативные English документы остаются в `docs/`; русские переводы находятся в `docs/locales/ru/` и не заменяют code-facing contracts или machine-readable evidence.

## 2026-08-18 — Unified external evidence readiness matrix

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| EXT-01 | Environment digest и deterministic signed receipt | `DONE / LOCAL VERIFIED` | `ingest_runner_result.py` добавляет `environment_digest` и `receipt_id`; `verify_evidence()` отклоняет stale/mismatched receipt |
| EXT-02 | Unified readiness matrix для Hermes/OpenCode/DeepSeek Harness | `DONE / LOCAL VERIFIED` | `scripts/external_evidence_readiness.py`; schema `noesis.external-evidence-readiness.v1`; статусы `passed/not_run/blocked/unsupported` |
| EXT-03 | Current machine-readable readiness artifact | `DONE / LOCAL VERIFIED / EXTERNAL NOT RUN` | `docs/EXTERNAL_EVIDENCE_READINESS_MATRIX.json`; все три lanes сейчас `not_run` из-за пустых exact revisions; `native_or_external_execution_claim=false` |
| EXT-04 | Negative cases | `DONE / LOCAL VERIFIED` | Missing revision, revision mismatch, environment mismatch, stale receipt, duplicate system record, protocol fingerprint conflict и unsupported lane покрыты `tests/test_external_evidence_readiness.py` |
| EXT-05 | Contract/localization | `DONE / LOCAL VERIFIED` | `docs/EXTERNAL_EVIDENCE_READINESS.md` и `docs/locales/ru/EXTERNAL_EVIDENCE_READINESS_RU.md`; signed evidence contract обновлён |

Этот gate подтверждает только readiness и integrity ingestion. Реальные Hermes/OpenCode/DeepSeek Harness execution, native Windows/macOS execution и comparative superiority остаются `not_run/blocked` до exact revisions, matching environments, disposable workspaces и explicit approval.

## 2026-08-18 — Release audit external-readiness claim guard

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| REL-03 | Интегрировать readiness matrix в read-only release audit | `DONE / LOCAL VERIFIED` | `scripts/release_audit.py` проверяет schema, четыре допустимых статуса, наличие lanes и `native_or_external_execution_claim=false` |
| REL-04 | Fail-closed invalid readiness artifact | `DONE / LOCAL VERIFIED` | Некорректная schema, отсутствующие lanes или внешний claim делают release audit `clean=false`; ожидаемый `overall_status=not_run` разрешён |
| REL-05 | Release boundary documentation | `DONE / LOCAL VERIFIED` | `docs/RELEASE_AUDIT_EXTERNAL_READINESS.md`; native/external execution и superiority ranking не создаются локальным audit |

Release audit остаётся локальным/private gate. `not_run` для внешних lanes является честным состоянием отсутствия exact revisions и matching hosts, а не скрытым pass/fail.

## 2026-08-18 — Native evidence honesty gate

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| NAT-07 | Portable SHA/SBOM lane | `DONE / LOCAL VERIFIED` | `scripts/run_parallel_native_evidence_lanes.py`; portable fixture verification `passed` |
| NAT-08 | Static Windows/macOS manifests | `DONE / LOCAL VERIFIED` | Static manifest lane `passed`; `native_builds_executed=false` |
| NAT-09 | Python 3.14 identity lane | `DONE / LOCAL VERIFIED` | Local interpreter `3.14.7`; target-host packaging не заявляется |
| NAT-10 | Target-host honesty matrix | `DONE / LOCAL VERIFIED` | Windows и macOS verifier lanes `passed` как honesty checks; actual evidence для обоих `not_run: target_host_or_python_mismatch` |

Machine evidence: `docs/PARALLEL_NATIVE_EVIDENCE.json`; English contract: `docs/NATIVE_EVIDENCE_HONESTY_GATE.md`. Реальные Windows `.exe`, macOS `.app`, Authenticode/codesign/notarization и native execution требуют matching target hosts.

## 2026-08-18 — Cross-platform release gate matrix

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| XPLAT-01 | Aggregate local/native/external matrix | `DONE / LOCAL VERIFIED` | `scripts/build_cross_platform_gate_matrix.py`; schema `noesis.cross-platform-release-gates.v1` |
| XPLAT-02 | Current Linux local verifier | `passed` | Bounded native-evidence lanes прошли; network/credentials/model-generated code disabled |
| XPLAT-03 | Windows/macOS native gates | `not_run / EXTERNAL HOST REQUIRED` | `target_host_or_python_mismatch`; native `.exe/.app` claim не создан |
| XPLAT-04 | Hermes/OpenCode/DeepSeek external gates | `not_run / EXTERNAL ENV REQUIRED` | Exact immutable revisions отсутствуют; comparative readiness `false` |
| XPLAT-05 | Claim boundary and negative status validation | `DONE / LOCAL VERIFIED` | Invalid status values fail closed to `blocked`; `native_or_external_execution_claim=false` |

Machine evidence: `docs/CROSS_PLATFORM_RELEASE_GATE_MATRIX.json`; English contract: `docs/CROSS_PLATFORM_RELEASE_GATES.md`.

## 2026-08-18 — Build policy honesty gate

| ID | Задача | Статус | Доказательство |
|---|---|---|---|
| BUILD-06 | Windows/macOS packaging dry-run | `DONE / LOCAL VERIFIED` | `scripts/run_parallel_build_policy_lanes.py`; обе команды `passed`, но `run_permitted=false` на Linux host |
| BUILD-07 | Signing policy presence | `DONE / LOCAL VERIFIED` | Authenticode и codesign requirements проверены; `native_builds_executed=false` |
| BUILD-08 | Python 3.14 build-policy identity | `DONE / LOCAL VERIFIED` | Local Python `3.14.7`; target-host artifact не заявляется |
| BUILD-09 | Build refusal boundary | `DONE / LOCAL VERIFIED` | `network_allowed=false`, `credentials_available=false`, `model_generated_code_executed=false` |

Machine evidence: `docs/PARALLEL_BUILD_POLICY_EVIDENCE.json`; English contract: `docs/BUILD_POLICY_HONESTY_GATE.md`. Реальные `.exe/.app`, signatures и notarization требуют matching target hosts.

## 2026-08-18 — Parallel agent tracks

| ID | Track | Статус | Доказательство |
|---|---|---|---|
| PAR-01 | Reliability/recovery и chaos | `DONE / LOCAL VERIFIED` | Recovery: 7 tests; chaos: 4 tests; оба track passed |
| PAR-02 | Security holdouts и docs security | `DONE / LOCAL VERIFIED` | Security/holdout suites и docs security audit passed |
| PAR-03 | Operator/UI/portable conformance | `DONE / LOCAL VERIFIED` | UI/portable suites и native/build-policy validators passed |
| PAR-04 | Release/evidence/docs audit | `DONE / LOCAL VERIFIED` | Links, JSON evidence, release metadata и remote parity passed |
| PAR-05 | Isolation and claim boundary | `DONE / LOCAL VERIFIED` | `network_allowed=false`, `credentials_available=false`, `external_processes_started=false`; native/external claims не создавались |

Machine evidence: `docs/PARALLEL_AGENT_TRACKS_EVIDENCE.json`; English contract: `docs/PARALLEL_AGENT_TRACKS.md`. Отсутствующий rollback glob не был засчитан как pass: он явно исключён из финального Track A status из-за отсутствия matching test file.

## 2026-08-18 — Parallel agent tracks 2

| ID | Track | Статус | Доказательство |
|---|---|---|---|
| PAR2-01 | Task/session API, SSE и recovery | `DONE / LOCAL VERIFIED` | 28 тестов: session 11, task 6, stream 4, recovery 7 |
| PAR2-02 | Child runtime и sandbox | `DONE / LOCAL VERIFIED` | Sandbox 7, child 12; Linux Bubblewrap passed; macOS/Windows `not_run` |
| PAR2-03 | Memory/provenance/governance | `DONE / LOCAL VERIFIED` | Memory 3, governance 5; docs security `CLEAN` |
| PAR2-04 | Release/UI/operator contract | `DONE / LOCAL VERIFIED` | UI 11, portable 12; links/release metadata passed |
| PAR2-05 | Neutral coverage accounting | `DONE / LOCAL VERIFIED` | Empty process/provenance/leak/operator globs recorded as `0`, never as fabricated pass |

Machine evidence: `docs/PARALLEL_AGENT_TRACKS_2_EVIDENCE.json`; English contract: `docs/PARALLEL_AGENT_TRACKS_2.md`. Native macOS/Windows и external Hermes/OpenCode/DeepSeek Harness claims не создавались.

## 2026-08-18 — Third parallel stage

| ID | Track/gate | Статус | Доказательство |
|---|---|---|---|
| STAGE3-A01 | Native Windows/macOS sandbox preflight | `LOCAL VERIFIED / TARGET HOST NOT_RUN` | Linux Bubblewrap `passed`; macOS sandbox-exec и Windows native `not_run`; claims не повышены |
| STAGE3-A02 | External Hermes/OpenCode/DeepSeek preflight | `NOT_RUN / EXACT REVISION REQUIRED` | Все три lanes `not_run`; `comparative_ready=false`; external execution claim `false` |
| STAGE3-B01 | Python 3.14 full-suite performance profile | `DONE / LOCAL VERIFIED` | 383 tests, subprocess wall-time 19.465471 s, in-process wall-time 19.758539 s, child max RSS 43156 KiB, peak tracemalloc 3159979 bytes, ResourceWarning 0 |
| STAGE3-C01 | Operator telemetry dashboard | `DONE / LOCAL VERIFIED` | `/api/telemetry`, `/api/child-runtimes`, bounded SSE `/api/telemetry/events`; secret redaction tests passed |
| STAGE3-C02 | Dashboard safety boundary | `DONE / LOCAL VERIFIED` | Read-only telemetry; no provider/tool invocation; loopback/auth gates inherited |

Machine artifacts: `docs/PYTHON314_TEST_PERFORMANCE_PROFILE.json`, `docs/STAGE3_EXTERNAL_READINESS_PREFLIGHT.json`, `docs/STAGE3_CROSS_PLATFORM_PREFLIGHT.json`. English contract: `docs/OPERATOR_TELEMETRY_DASHBOARD.md`; Russian localization: `docs/locales/ru/OPERATOR_TELEMETRY_DASHBOARD_RU.md`.

## 2026-08-18 — Parallel Stage 4

| ID | Track/gate | Статус | Доказательство |
|---|---|---|---|
| STAGE4-A01 | Performance repeatability | `DONE / LOCAL VERIFIED` | 383 tests; wall-time 19.481825 s; in-process 19.756480 s; RSS 43196 KiB; tracemalloc 3159784 bytes; warnings 0 |
| STAGE4-B01 | Telemetry robustness | `DONE / LOCAL VERIFIED` | 12 UI/health/auth tests; docs security `CLEAN`; SSE glob coverage recorded neutral because no dedicated matching file exists |
| STAGE4-C01 | Packaging/evidence honesty | `DONE / LOCAL VERIFIED` | Native/build-policy validators, JSON evidence and release metadata passed; external readiness `not_run` |
| STAGE4-C02 | Claim boundary | `DONE / LOCAL VERIFIED` | Network/credentials disabled; no native or external process started |

Machine evidence: `docs/PARALLEL_STAGE4_EVIDENCE.json`; English report: `docs/PARALLEL_STAGE4.md`; Russian localization: `docs/locales/ru/PARALLEL_STAGE4_RU.md`.

## 2026-08-18 — Self-Learning / OS / Documentation Sync Audit

| ID | Gate | Статус | Вывод |
|---|---|---|---|
| AUDIT-SL-01 | Self-learning maturity audit | `DONE / LOCAL VERIFIED` | Memory, provenance, experience reuse и governance реализованы; полный observe→evaluate→propose→approve→promote→verify product loop ещё не завершён |
| AUDIT-OS-01 | Agent OS/control-plane audit | `DONE / LOCAL VERIFIED / BOUNDED` | Sessions, tasks, approvals, recovery, child runtime, Linux sandbox, SSE telemetry и operator dashboard реализованы; native Windows/macOS остаются `not_run` |
| AUDIT-SYNC-01 | Code/docs/GitHub synchronization audit | `DONE / LOCAL VERIFIED` | English primary, Russian locale, links, security, evidence, release metadata и remote parity проверены |
| NEXT-SL-01 | Human-Governed Learning Promotion Pipeline | `NEXT LOCAL GATE` | Experience receipt → deterministic holdout evaluator → review proposal → explicit approval → immutable promotion → rollback/holdout verification → signed receipt |

English primary audit: `docs/SELF_LEARNING_OS_SYNC_AUDIT.md`; Russian supplemental localization: `docs/locales/ru/SELF_LEARNING_OS_SYNC_AUDIT_RU.md`.

## 2026-08-18 — Human-Governed Learning Promotion Pipeline

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-01 | Provenance-bound experience receipt | `DONE / LOCAL VERIFIED` | `noesis_harness/learning_promotion.py`; source/policy/payload digests, scope и schema binding |
| LEARN-02 | Deterministic holdout evaluator | `DONE / LOCAL VERIFIED` | Sorted case digest; non-empty all-pass and zero-leakage acceptance |
| LEARN-03 | Review-only learning proposal | `DONE / LOCAL VERIFIED` | Proposal remains `review` until explicit operator approval |
| LEARN-04 | Explicit approval and immutable promotion | `DONE / LOCAL VERIFIED` | Approval identity, passing tests, immutable version directory and content digest |
| LEARN-05 | Rollback and signed promotion receipt | `DONE / LOCAL VERIFIED` | ACTIVE pointer rollback and HMAC-SHA256 promotion receipt |
| LEARN-06 | Executable skill boundary | `DONE / BOUNDED` | Promotion module never executes skill content; entrypoints remain disabled |
| LEARN-07 | Full integration with autonomous runtime | `NEXT LOCAL GATE` | Connect promotion lifecycle to task completion/evaluator/operator telemetry without automatic activation |

English primary contract: `docs/LEARNING_PROMOTION_PIPELINE.md`; Russian supplemental localization: `docs/locales/ru/LEARNING_PROMOTION_PIPELINE_RU.md`.

## 2026-08-18 — Learning Promotion Integration

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-INT-01 | Terminal task → experience receipt | `DONE / LOCAL VERIFIED` | Active/unknown tasks rejected; terminal outcomes capture provenance-bound receipt |
| LEARN-INT-02 | Explicit evaluator registry | `DONE / LOCAL VERIFIED` | Duplicate/unknown evaluator versions fail closed; no implicit evaluator |
| LEARN-INT-03 | Review-only operator lifecycle | `DONE / LOCAL VERIFIED` | Capture/evaluate/propose/approve/promote/rollback are explicit operations |
| LEARN-INT-04 | Promotion telemetry and HealthServer snapshot | `DONE / LOCAL VERIFIED` | Bounded redacted `learning_promotion` section; existing SSE snapshot remains read-only |
| LEARN-INT-05 | Automatic activation boundary | `DONE / BOUNDED` | Integration defaults `activate=False`; task completion and evaluator never activate skills |
| LEARN-INT-06 | Runtime evaluator/activation policy integration | `NEXT LOCAL GATE` | Connect to durable task event stream and policy simulator; keep activation separately gated |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-18 — Durable Promotion Event Bridge

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-EVT-01 | Replay terminal `task_state_changed` events | `DONE / LOCAL VERIFIED` | `committed` → success, `failed` → failure; non-terminal states ignored |
| LEARN-EVT-02 | Policy simulator boundary | `DONE / LOCAL VERIFIED` | Explicit allow plus source/policy digests, agent identity and scope required |
| LEARN-EVT-03 | Durable idempotent checkpoints | `DONE / LOCAL VERIFIED` | Started/completed/denied records keyed by source event ID; repeated poll skips terminal checkpoint |
| LEARN-EVT-04 | Fail-closed denial | `DONE / LOCAL VERIFIED` | Policy deny, malformed response, simulator exception and cancelled task create no receipt |
| LEARN-EVT-05 | Crash-safe receipt retry | `DONE / BOUNDED` | Existing receipt reused by experience ID; operator approval/promotion remain outside replay |
| LEARN-EVT-06 | Durable task stream and policy simulator production wiring | `NEXT LOCAL GATE` | Supply runtime-owned policy simulator and connect bridge polling to operator execution lifecycle |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-18 — Runtime-Owned Policy and Operator Lifecycle Wiring

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-RUNTIME-01 | Runtime-owned deterministic policy simulator | `DONE / LOCAL VERIFIED` | `RuntimePolicySimulator` produces stable source/policy digests and performs no side effects |
| LEARN-RUNTIME-02 | Explicit operator lifecycle trigger | `DONE / LOCAL VERIFIED` | `TaskExecutionBridge.poll_promotion_events(operator_trigger=True)` required; `execute()` never polls implicitly |
| LEARN-RUNTIME-03 | Runtime promotion wiring | `DONE / LOCAL VERIFIED` | Bridge and simulator are injected explicitly; missing runtime configuration fails closed |
| LEARN-RUNTIME-04 | Approval/activation boundary | `DONE / BOUNDED` | Capture only; evaluator, approval, promotion and activation remain separate explicit operations |
| LEARN-RUNTIME-05 | Runtime-owned production policy configuration | `NEXT LOCAL GATE` | Replace fixture-level simulator configuration with policy derived from runtime/session ownership metadata |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-18 — Ownership-Derived Policy and Operator Approval Actions

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-OWNER-01 | Authoritative ownership-derived policy | `DONE / LOCAL VERIFIED` | `OwnershipPolicySimulator` validates task/session identity and resolves owner through explicit runtime lookup |
| LEARN-OWNER-02 | Scope and metadata fail-closed checks | `DONE / LOCAL VERIFIED` | Session mismatch, missing owner, denied scope and lookup errors create no receipt |
| LEARN-OWNER-03 | Versioned operator approval action | `DONE / LOCAL VERIFIED` | `PromotionApprovalAction` accepts only `approve`, `reject`, `rollback` under `noesis.promotion-approval.v1` |
| LEARN-OWNER-04 | UI handler boundary | `DONE / LOCAL VERIFIED` | Optional `POST /api/promotion-actions` validates and delegates; HealthServer never performs promotion |
| LEARN-OWNER-05 | Automatic activation prohibition | `DONE / BOUNDED` | UI action validation and policy simulation cannot create active skill pointers |
| LEARN-OWNER-06 | Real operator action implementation | `NEXT LOCAL GATE` | Bind injected handler to explicit proposal approve/reject/rollback operations with independent reviewer policy |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-18 — Explicit Operator Action Executor

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-ACTION-01 | Explicit approve/reject/rollback executor | `DONE / LOCAL VERIFIED` | `PromotionActionExecutor` maps versioned actions to separate proposal transitions |
| LEARN-ACTION-02 | Independent reviewer policy | `DONE / LOCAL VERIFIED` | Operator identity cannot equal experience owner for approval actions |
| LEARN-ACTION-03 | Signed action receipt | `DONE / LOCAL VERIFIED` | HMAC-signed `noesis.promotion-action-receipt.v1` receipt verifies against canonical action fields |
| LEARN-ACTION-04 | Idempotent action replay | `DONE / LOCAL VERIFIED` | Repeated `action_id` returns stored receipt and does not reapply state transition |
| LEARN-ACTION-05 | Activation boundary | `DONE / BOUNDED` | Approval/rejection/rollback executor never activates a skill; promotion remains separate |
| LEARN-ACTION-06 | UI handler binding | `DONE / LOCAL VERIFIED` | HealthServer action route delegates only to injected handler after schema validation |
| LEARN-ACTION-07 | Full operator proposal workflow | `NEXT LOCAL GATE` | Bind handler to operator session/auth identity and independent reviewer policy in production UI lifecycle |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-18 — Operator Authorization Context and Audit Telemetry

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-AUTH-01 | Operator identity/session context | `DONE / LOCAL VERIFIED` | `OperatorAuthContext` must match action operator identity and configured session |
| LEARN-AUTH-02 | Optional scope authorization | `DONE / LOCAL VERIFIED` | Action scope is accepted only when present in configured operator scopes |
| LEARN-AUTH-03 | HealthServer request binding | `DONE / LOCAL VERIFIED` | `/api/promotion-actions` delegates action plus configured context; token-only/anonymous context is denied |
| LEARN-AUTH-04 | Conflict and denial telemetry | `DONE / LOCAL VERIFIED` | Identity/session/scope/reviewer/state conflicts emit bounded `promotion_action_denied` events |
| LEARN-AUTH-05 | Replay audit | `DONE / LOCAL VERIFIED` | Replayed `action_id` emits `promotion_action_replayed` without duplicate state transition |
| LEARN-AUTH-06 | Production operator identity source | `NEXT LOCAL GATE` | Bind context to authenticated operator session lifecycle and independent reviewer authorization store |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-18 — Persistent Reviewer Authorization Store

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-REVIEW-01 | Persistent reviewer grant store | `DONE / LOCAL VERIFIED` | Append-only `ReviewerAuthorizationStore` persists operator/session grants and scopes |
| LEARN-REVIEW-02 | Revocation and recovery | `DONE / LOCAL VERIFIED` | Revoked grant overrides prior grant after store reconstruction |
| LEARN-REVIEW-03 | Fail-closed default | `DONE / LOCAL VERIFIED` | Missing authorization, inactive grant and scope mismatch deny review |
| LEARN-REVIEW-04 | Executor integration | `DONE / LOCAL VERIFIED` | `PromotionActionExecutor` requires authorized independent reviewer when store is configured |
| LEARN-REVIEW-05 | Activation boundary | `DONE / BOUNDED` | Reviewer authorization changes proposal state only; it never activates a skill |
| LEARN-REVIEW-06 | Production identity source | `NEXT LOCAL GATE` | Bind reviewer store grants to authenticated operator session lifecycle and durable administrative policy |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-18 — Durable Operator Session Lifecycle

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-SESSION-01 | Persistent operator session registry | `DONE / LOCAL VERIFIED` | `OperatorSessionRegistry` stores open/close events and reconstructs current session state |
| LEARN-SESSION-02 | TTL expiration | `DONE / LOCAL VERIFIED` | Expired sessions derive unauthenticated context and cannot authorize review |
| LEARN-SESSION-03 | Close/revoke behavior | `DONE / LOCAL VERIFIED` | Closed sessions fail active validation after restart/replay |
| LEARN-SESSION-04 | Reviewer executor binding | `DONE / LOCAL VERIFIED` | `PromotionActionExecutor` requires active session when registry is configured |
| LEARN-SESSION-05 | No implicit activation | `DONE / BOUNDED` | Session lifecycle only controls authorization; it never promotes or activates skills |
| LEARN-SESSION-06 | Administrative policy source | `NEXT LOCAL GATE` | Replace local injected session configuration with a reviewed administrative policy lifecycle and operator UI integration |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-18 — Reviewed Administrative Policy and Session UI Actions

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-ADMIN-01 | Reviewed reviewer grant/revoke policy | `DONE / LOCAL VERIFIED` | `AdministrativePolicyStore` requires active admin session and `admin:reviewers` scope |
| LEARN-ADMIN-02 | Unauthorized admin mutation denial | `DONE / LOCAL VERIFIED` | Non-admin or expired admin context is rejected before reviewer policy mutation |
| LEARN-ADMIN-03 | Explicit operator session actions | `DONE / LOCAL VERIFIED` | `OperatorSessionAction` and executor implement only open/close with idempotent replay |
| LEARN-ADMIN-04 | Safe UI mutation endpoints | `DONE / LOCAL VERIFIED` | `/api/operator-sessions` and `/api/admin/reviewer-policy` validate and delegate only via POST handlers |
| LEARN-ADMIN-05 | No implicit promotion/activation | `DONE / BOUNDED` | Administrative operations cannot create active skill pointers or trigger promotion |
| LEARN-ADMIN-06 | External identity provider | `NEXT LOCAL GATE` | Replace local admin allow-list with reviewed external/operator identity integration when a pinned provider exists |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-18 — Signed Administrative Mutation Evidence

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-EVIDENCE-01 | Signed mutation receipt | `DONE / LOCAL VERIFIED` | HMAC-signed `noesis.signed-mutation-receipt.v1` for admin and session mutations |
| LEARN-EVIDENCE-02 | Tamper verification | `DONE / LOCAL VERIFIED` | `verify_signed_mutation_receipt` rejects changed fields and wrong keys |
| LEARN-EVIDENCE-03 | Conflict detection | `DONE / LOCAL VERIFIED` | Repeated grant/revoke/open/close state is rejected before unsafe duplicate mutation |
| LEARN-EVIDENCE-04 | Interrupted-tail recovery | `DONE / LOCAL VERIFIED` | EventStore repairs only malformed final JSONL tail; non-tail corruption remains hard failure |
| LEARN-EVIDENCE-05 | Audit boundary | `DONE / BOUNDED` | Mutation receipts attest policy/session changes only; they do not attest promotion or skill activation |
| LEARN-EVIDENCE-06 | Atomic multi-log commit | `NEXT LOCAL GATE` | Replace sequential cross-store mutation/audit append with a transaction-coordinated journal when needed |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-18 — Coordinated Mutation Journal

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-JOURNAL-01 | Durable prepare/commit journal | `DONE / LOCAL VERIFIED` | `CoordinatedMutationJournal` records `prepared`, `committed`, `aborted` phases |
| LEARN-JOURNAL-02 | Incomplete mutation visibility | `DONE / LOCAL VERIFIED` | `status()` returns `incomplete`; `incomplete()` lists prepared actions without terminal record |
| LEARN-JOURNAL-03 | Executor wiring | `DONE / LOCAL VERIFIED` | Admin reviewer and session mutation executors optionally coordinate with the journal |
| LEARN-JOURNAL-04 | Fail-closed recovery | `DONE / BOUNDED` | Interrupted operation is visible and not auto-promoted or silently reconciled |
| LEARN-JOURNAL-05 | Honest atomicity boundary | `DONE / BOUNDED` | The journal coordinates separate logs but does not claim cross-file atomic commit |
| LEARN-JOURNAL-06 | Single-store transactional backend | `NEXT LOCAL GATE` | Move state and audit records to a transaction-coordinated SQLite/WAL journal when required |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-18 — SQLite/WAL Transactional Administrative Backend

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-SQLITE-01 | Single-store SQLite/WAL schema | `DONE / LOCAL VERIFIED` | Sessions, reviewer grants and mutation audit are stored in one SQLite database |
| LEARN-SQLITE-02 | Transactional state + audit commit | `DONE / LOCAL VERIFIED` | Accepted mutation writes state and signed audit row in one transaction |
| LEARN-SQLITE-03 | Rollback/no orphan evidence | `DONE / LOCAL VERIFIED` | Denied actor/session and conflict paths leave no audit row or partial state |
| LEARN-SQLITE-04 | Restart/recovery | `DONE / LOCAL VERIFIED` | Reopened backend reconstructs sessions and detects active-state conflicts |
| LEARN-SQLITE-05 | Resource hygiene | `DONE / LOCAL VERIFIED` | Managed connections close cleanly under Python 3.14 ResourceWarning policy |
| LEARN-SQLITE-06 | Runtime adoption | `DONE / BOUNDED LOCAL` | Portable launcher supports explicit SQLite/WAL admin backend adoption only when a valid signing key is configured; default remains fail-closed/legacy |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-18 — Administrative Store Migration Adapter

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-MIGRATE-01 | Versioned migration state | `DONE / LOCAL VERIFIED` | `noesis.admin-migration.v1` with `legacy`, `dual_read`, `sqlite` modes |
| LEARN-MIGRATE-02 | Direct cutover prevention | `DONE / LOCAL VERIFIED` | `legacy` cannot jump directly to `sqlite` |
| LEARN-MIGRATE-03 | Dual-read verification | `DONE / LOCAL VERIFIED` | Identity, scopes and active state compare; TTL timestamp jitter is semantic-only |
| LEARN-MIGRATE-04 | Mismatch fail-closed | `DONE / LOCAL VERIFIED` | State mismatch returns `blocked` and `require_dual_read` raises |
| LEARN-MIGRATE-05 | Explicit rollback | `DONE / LOCAL VERIFIED` | `sqlite`/`dual_read` can explicitly roll back to `legacy` |
| LEARN-MIGRATE-06 | Automatic cutover | `NOT_RUN / DISABLED` | No silent replacement of append-only stores |
| LEARN-MIGRATE-07 | Production routing adoption | `DONE / BOUNDED LOCAL` | Operator mode source is wired to HealthServer readiness and portable startup; automatic cutover remains disabled |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-18 — Explicit Administrative Action Routing

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-ROUTE-01 | Legacy default | `DONE / LOCAL VERIFIED` | Router selects legacy handler when migration mode is unset |
| LEARN-ROUTE-02 | Dual-read guard | `DONE / LOCAL VERIFIED` | Failed projection verification blocks operator routing |
| LEARN-ROUTE-03 | SQLite selection | `DONE / LOCAL VERIFIED` | SQLite handler is selected only after verified dual-read and explicit mode transition |
| LEARN-ROUTE-04 | HealthServer handler | `DONE / BOUNDED` | `health_handler()` delegates validated action/context without performing implicit promotion |
| LEARN-ROUTE-05 | Routing evidence | `DONE / LOCAL VERIFIED` | Bounded `administrative_action_routed` event records mode and verification result |
| LEARN-ROUTE-06 | Automatic cutover | `NOT_RUN / DISABLED` | No silent replacement of legacy stores |
| LEARN-ROUTE-07 | Production executor replacement | `NEXT LOCAL GATE` | Remaining Gate 1: bind real PromotionActionExecutor to authenticated operator lifecycle and independent reviewer policy in deployment configuration |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-18 — Promotion Executor Production Wiring

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-WIRE-01 | Executor-aware router | `DONE / LOCAL VERIFIED` | `promotion_handler()` parses `PromotionApprovalAction` and delegates to executor `handle()` |
| LEARN-WIRE-02 | Authorization preservation | `DONE / LOCAL VERIFIED` | Router does not bypass executor reviewer/session/identity checks |
| LEARN-WIRE-03 | HealthServer injection | `DONE / BOUNDED` | Handler is compatible with HealthServer injected mutation route; no GET/SSE side effects |
| LEARN-WIRE-04 | Legacy default | `DONE / LOCAL VERIFIED` | Legacy executor remains selected unless migration mode changes explicitly |
| LEARN-WIRE-05 | SQLite guard | `DONE / LOCAL VERIFIED` | SQLite executor selection requires verified dual-read and explicit `sqlite` mode |
| LEARN-WIRE-06 | Automatic activation | `NOT_RUN / DISABLED` | Router cannot activate skills or infer promotion from routing evidence |
| LEARN-WIRE-07 | Deployment adoption | `NEXT LOCAL GATE` | Remaining Gate 1: bind handler to concrete deployment configuration with durable operator session and reviewer policy |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-18 — Operator-Owned Migration Readiness

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-READY-01 | Operator-owned mode source | `DONE / LOCAL VERIFIED` | Append-only `OperatorMigrationModeSource`; safe default is `legacy` |
| LEARN-READY-02 | Mode authorization | `DONE / LOCAL VERIFIED` | Optional operator allow-list; unauthorized mode changes fail closed |
| LEARN-READY-03 | Direct sqlite cutover guard | `DONE / LOCAL VERIFIED` | `legacy -> sqlite` is rejected without `dual_read` |
| LEARN-READY-04 | HealthServer startup wiring | `DONE / LOCAL VERIFIED` | Mode source is read during startup and health/readiness generation |
| LEARN-READY-05 | Readiness snapshot | `DONE / LOCAL VERIFIED` | Reports mode, blocked, rollback_available, operator_owned and automatic_cutover=false |
| LEARN-READY-06 | Readiness endpoint | `DONE / LOCAL VERIFIED` | `GET /api/readiness` is read-only and authenticated when configured |
| LEARN-READY-07 | Blocked UI mapping | `DONE / LOCAL VERIFIED` | Machine snapshot remains `blocked`; UI health status maps to allowed `unavailable` |
| LEARN-READY-08 | Automatic mode change | `NOT_RUN / DISABLED` | Startup never changes migration mode or performs cutover |
| LEARN-READY-09 | Native/external readiness | `NOT_RUN` | Windows/macOS and external A/B remain environment-gated |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-18 — UI Migration Readiness and Signed Mode Changes

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-UI-01 | Readiness in control-plane UI | `DONE / LOCAL VERIFIED` | Cloudflare-style policy card shows mode, status and rollback availability |
| LEARN-UI-02 | Readiness in SSE | `DONE / LOCAL VERIFIED` | `/api/telemetry/events` carries `migration_readiness` and UI refreshes the same panel |
| LEARN-UI-03 | Signed mode-change action | `DONE / LOCAL VERIFIED` | `OperatorMigrationModeSource.handle_action()` returns HMAC receipt |
| LEARN-UI-04 | Authenticated mode endpoint | `DONE / LOCAL VERIFIED` | POST `/api/admin/migration-mode` requires configured operator context |
| LEARN-UI-05 | Receipt tamper detection | `DONE / LOCAL VERIFIED` | `verify_signed_mode_change_receipt()` rejects changed fields |
| LEARN-UI-06 | Legacy default | `DONE / LOCAL VERIFIED` | Startup and UI default to legacy; no automatic cutover |
| LEARN-UI-07 | Mode-change authorization | `DONE / LOCAL VERIFIED` | Operator allow-list and identity mismatch fail closed |
| LEARN-UI-08 | Native/external readiness | `NOT_RUN` | Windows/macOS and external A/B remain environment-gated |

## 2026-08-18 — Roadmap reconciliation and persistent migration audit checkpoint

| ID | Gate | Status | Evidence |
|---|---|---|---|
| RECON-01 | English master roadmap | `DONE / LOCAL VERIFIED` | `docs/PLAN_NOESIS_1.0_MASTER.md` is now the status-driven normative plan with measurable Gates 1–7 |
| RECON-02 | Russian master localization | `DONE / LOCAL VERIFIED` | `docs/locales/ru/PLAN_NOESIS_1.0_MASTER_RU.md` mirrors the English gate order and claim boundary |
| RECON-03 | Self-learning maturity synchronization | `DONE / LOCAL VERIFIED` | English/Russian self-learning audits now record completed promotion primitives and the remaining production lifecycle binding gate |
| RECON-04 | Migration receipt persistence | `DONE / LOCAL VERIFIED` | Signed mode-change receipts persist transactionally in SQLite/WAL and survive backend reopen |
| RECON-05 | Audit timeline contract | `DONE / LOCAL VERIFIED` | `/api/audit/migration`, telemetry snapshot and SSE/UI timeline render bounded signed receipts |
| NEXT-01 | Production learning lifecycle binding | `DONE / BOUNDED LOCAL` | `ProductionLearningLifecycle` and portable launcher compose terminal capture, runtime policy, authenticated configuration and explicit operator actions; automatic activation remains disabled |
| BLOCKED-01 | Native Windows/macOS evidence | `NOT_RUN / HOST REQUIRED` | Matching hosts and Python 3.14 native evidence are unavailable in the local lane |
| BLOCKED-02 | External Hermes/OpenCode/DeepSeek A/B | `NOT_RUN / PINNED ENV REQUIRED` | Exact revisions, executables, disposable environments and signed operator-approved runs are unavailable |

### Production learning lifecycle facade

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| LEARN-PROD-01 | Explicit lifecycle composition | `DONE / BOUNDED LOCAL` | `ProductionLearningLifecycle` composes durable task store, event bridge, injected policy simulator and action executor |
| LEARN-PROD-02 | Operator-trigger boundary | `DONE / LOCAL VERIFIED` | Capture without `operator_trigger=True` fails closed; terminal capture is replay-idempotent |
| LEARN-PROD-03 | Automatic activation boundary | `DONE / LOCAL VERIFIED` | Readiness reports automatic evaluation/approval/promotion/activation disabled |
| LEARN-PROD-04 | Concrete deployment binding | `DONE / BOUNDED LOCAL` | Portable launcher binds the facade to persistent session/reviewer stores and the injected HealthServer promotion action handler when signing configuration is explicit |
| LEARN-PROD-05 | Durable promotion state/evaluator deployment | `DONE / LOCAL VERIFIED` | SQLite/WAL persistence, restart reconstruction, evaluator manifest conflict rejection, duplicate idempotency and bounded HealthServer/UI/SSE snapshot; 430-test full suite |
| NEXT-03 | Governed executable child runtime | `IN PROGRESS / BOUNDED LOCAL` | Manifest/grant contract, strict hardened-backend requirement and Linux/Bubblewrap filesystem/network isolation are verified; remaining receipt/diff/recovery integration and native backend evidence are open |

### Gate 3 child runtime evidence

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-01 | Versioned manifest binding | `DONE / LOCAL VERIFIED` | `ExecutionRequest` validates skill identity and binds `SkillManifest` to the request |
| CHILD-02 | Explicit capability grants | `DONE / LOCAL VERIFIED` | Missing grant and identity mismatch fail closed; committed Gatekeeper decision remains required |
| CHILD-03 | Hardened backend boundary | `DONE / BOUNDED LOCAL` | Strict skill mode rejects absent backend; Bubblewrap uses unshare-all/unshare-net and workspace-only write binding |
| CHILD-04 | Filesystem/network adversarial isolation | `DONE / LINUX VERIFIED` | Child probe blocks host-path read and outbound socket; Windows/macOS remain `not_run` |
| CHILD-05 | Signed execution receipt, diff review and recovery integration | `DONE / BOUNDED LOCAL` | HMAC receipt persistence/replay, durable patch proposal/review state and interrupted-run recovery ledger are verified; review does not apply patches |
| CHILD-06 | Operator-controlled rollback/recovery binding | `DONE / BOUNDED LOCAL` | Authenticated `ExecutionRecoveryExecutor` verifies signed receipt/run identity, approved patch, fresh base and handler-confirmed mutation; replay, stale-base, scope and unapproved-patch denials are tested |
| CHILD-07 | Native Windows/macOS child-runtime evidence | `NOT_RUN / HOST REQUIRED` | Requires matching hosts and native sandbox execution; Linux evidence must not be generalized |

### Gate 4 multi-agent work-product evidence

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| MA-01 | Exclusive task claim and per-agent workspace | `DONE / LOCAL VERIFIED` | Coordinator binds one task to one agent and creates isolated workspace |
| MA-02 | Typed work-product envelope | `DONE / BOUNDED LOCAL` | `WorkProductEnvelope` binds task, agent, workspace, base/head snapshots, result type and artifact digest |
| MA-03 | Independent review | `DONE / LOCAL VERIFIED` | Producing agent cannot review its own product; reviewer must be registered |
| MA-04 | Fresh-base merge authorization | `DONE / LOCAL VERIFIED` | Stale base and mismatched authorization fail closed; review never applies files |
| MA-05 | Explicit commit and durable resume/replay | `DONE / BOUNDED LOCAL` | Commit is separate from review; task/session/work-product events survive coordinator reopen |
| MA-06 | Bounded retry, leakage holdouts and work-product metrics | `DONE / BOUNDED LOCAL` | Retry limit is capped at 3, action reclaim is tested, cancellation is not retried, leakage corpus has 12 deterministic cases and evaluator reports correctness/delivery/leakage/recovery/reviewer-time/retry/commit metrics |
| MA-07 | Local parallel workload benchmark | `DONE / BOUNDED LOCAL` | Three parallel deterministic lanes, injected first-attempt crash, retry/reclaim, durable result aggregation, completed-run replay and aggregation conflict denial are verified |
| MA-08 | Crash-point recovery, active-lane leakage and repeated distributions | `DONE / BOUNDED LOCAL` | Before/after-write/read crash points recover, active-lane workspace escape is denied, three repeated runs produce deterministic mean/p50/p95 report with bounded repetitions |
| MA-09 | Simultaneous active-delegation leakage corpus | `DONE / BOUNDED LOCAL` | Four concurrent sibling-read/write, absolute-path and traversal probes are denied while lanes are active |

### Gate 5 memory and long-context evidence

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| MEM-01 | Recall | `DONE / BOUNDED LOCAL` | Source-ID intersection recall is deterministic and separate from attribution |
| MEM-02 | Attribution precision | `DONE / BOUNDED LOCAL` | Unsupported source attribution is penalized independently |
| MEM-03 | Conflict and temporal correctness | `DONE / BOUNDED LOCAL` | Recorded verifier booleans are measured separately; no model self-grading |
| MEM-04 | Compaction retention | `DONE / BOUNDED LOCAL` | Required source retention after compaction is measured explicitly |
| MEM-05 | Hard context budget | `DONE / BOUNDED LOCAL` | Used tokens over budget fail compliance; budget is never softened |
| MEM-06 | Durable trace and long-context stress | `DONE / BOUNDED LOCAL` | `DurableMemoryQualityAdapter` writes/reopens SQLite/WAL traces; 64-token fixtures run at scales 32/128/512/1024 over five repetitions |
| MEM-07 | Baseline versus nextgen distribution | `DONE / BOUNDED LOCAL` | Baseline recall mean 0.0, nextgen recall mean 1.0, gain 1.0; both budget compliance rates 1.0; fixture is deterministic and local-only |
| MEM-08 | Native Windows/macOS evidence preparation | `DONE / PREPARED NOT_RUN` | Fail-closed PowerShell/macOS bundles, environment digest contract and artifact requirements are ready; matching host execution remains `not_run` |
| MEM-09 | Durable memory traces with real long-context reuse | `NEXT LOCAL GATE` | Connect traces to broader context/reuse trajectories and non-fixture repeated stress distributions |

English primary: `docs/LEARNING_PROMOTION_INTEGRATION.md`; Russian supplemental: `docs/locales/ru/LEARNING_PROMOTION_INTEGRATION_RU.md`.

## 2026-08-20 — Human-governed promotion, durable checkpoints и multi-agent delegation checkpoint

| Gate | Статус | Evidence / boundary |
|---|---|---|
| Human-Governed Learning Promotion | `DONE / BOUNDED LOCAL` | Immutable content-addressed skill versions, review-only proposal, explicit approval, dual-signature verification, durable `PROMOTION_RECEIPT.json` и `VERSION.json`; focused promotion suites passed. |
| Durable Turn Checkpoints | `DONE / BOUNDED LOCAL` | SQLite/WAL per-turn persistence, sequential turn enforcement, canonical SHA-256 record/state digests, previous-digest chain, interrupted recovery, corruption rejection и zero ResourceWarning in focused suite. |
| Multi-Agent Delegation | `DONE / BOUNDED LOCAL` | Capability-scoped request, approval gate, isolated lane workspace, artifact manifest, HMAC-SHA256 review-only receipt и tamper rejection. |
| Cross-agent leakage under native OS isolation | `NOT_RUN / HOST-GATED` | Local workspace containment is tested; native Windows/macOS and external runtime isolation require matching hosts and disposable environments. |
| External Hermes/OpenCode/DeepSeek Harness A/B | `NOT_RUN / EXTERNAL-GATED` | Exact pinned revisions, executable availability, protocol fingerprints, environment digests and operator-approved evidence bundle are still required. |

Focused Python 3.14.7 evidence for this checkpoint: `38/38` tests passed with `-W error::ResourceWarning`; full regression remains mandatory before GitHub checkpoint.

## 2026-08-20 — MEM-09 real durable memory reuse checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| MEM-09 | Durable memory traces with real long-context reuse | `DONE / BOUNDED LOCAL` | `run_real_memory_reuse_stress` записывает факты через реальный `Memory.save`, получает selection через `Memory.recall`, сохраняет durable traces, reopen-ит SQLite после каждой repetition и агрегирует deterministic distribution digest; focused tests passed. |
| MEM-09-NATIVE | Native Windows/macOS memory evidence | `NOT_RUN / HOST REQUIRED` | Matching native hosts and signed target-host evidence remain unavailable in the local Linux lane. |
| MEM-09-EXTERNAL | External long-context A/B | `NOT_RUN / PINNED ENV REQUIRED` | Exact Hermes/OpenCode/DeepSeek Harness revisions, executables, protocol fingerprints, disposable environments and operator-approved receipts remain required. |

Current local MEM-09 fixture result: 4 repetitions × 24 distractors, 4/4 relevant facts recalled after reopen, persistence verified, deterministic distribution digest. This is local durability/retrieval evidence, not a general intelligence or superiority claim.


## 2026-08-20 — Gate 3 artifact-diff receipt checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-08 | Canonical child artifact manifest and diff | `DONE / BOUNDED LOCAL` | Before/after path-relative manifests, file size/SHA-256 entries, added/removed/changed diff и deterministic diff digest. |
| CHILD-09 | Signed receipt binding | `DONE / BOUNDED LOCAL` | `artifact_diff_digest` включён в stable receipt payload; HMAC verification, tamper rejection, stored payload verification и package export проверены. |
| CHILD-10 | Runtime integration | `DONE / BOUNDED LOCAL` | `ChildExecutionRuntime` снимает manifest до/после child run и передаёт diff в `ExecutionReceiptStore`; replay и recovery boundaries остаются fail-closed. |
| CHILD-11 | Native/external artifact evidence | `NOT_RUN / ENVIRONMENT-GATED` | Windows/macOS matching hosts и pinned external harness environments недоступны; нельзя обобщать Linux evidence. |

Gate 3 focused result after integration: `37/37` tests passed with Python 3.14.7 and `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 recovery replay assurance checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-12 | Recovery action fingerprint | `DONE / BOUNDED LOCAL` | Full action mapping получает deterministic fingerprint; duplicate exact replay is idempotent, changed payload under same action ID is rejected. |
| CHILD-13 | Artifact-aware rollback guard | `DONE / BOUNDED LOCAL` | Optional `artifact_diff_digest` action binding is compared with stored signed receipt before handler invocation; mismatch fails closed. |
| CHILD-14 | Recovery honesty | `DONE / BOUNDED LOCAL` | Rollback/recovery state and append-only completion event are written only after injected handler confirms transition. |
| CHILD-15 | Native/external recovery evidence | `NOT_RUN / ENVIRONMENT-GATED` | Matching Windows/macOS hosts and pinned external harness recovery environments remain unavailable. |

Focused recovery result: `29/29` assurance, recovery, child-runtime and export tests passed with Python 3.14.7 and `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 terminal lifecycle checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-16 | Terminal state transition guard | `DONE / BOUNDED LOCAL` | `running` может terminalize только один раз; update guarded by running state. |
| CHILD-17 | Exact completion idempotency | `DONE / BOUNDED LOCAL` | Exact duplicate terminal completion возвращает durable record без mutation. |
| CHILD-18 | Terminal conflict rejection | `DONE / BOUNDED LOCAL` | Другой status/workspace digest/receipt ID отклоняется с `execution_run_terminal_conflict`. |
| CHILD-19 | Native/external lifecycle evidence | `NOT_RUN / ENVIRONMENT-GATED` | Matching Windows/macOS hosts и pinned external harness environments остаются недоступны. |

Focused terminal lifecycle result: `30/30` assurance, recovery, child-runtime и export tests passed with Python 3.14.7 and `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 receipt-store audit checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-20 | Durable receipt audit snapshot | `DONE / BOUNDED LOCAL` | Все stored receipts проверяются в deterministic order; snapshot содержит count, IDs и aggregate digest. |
| CHILD-21 | Corruption fail-closed | `DONE / BOUNDED LOCAL` | Malformed payload, invalid digest/HMAC и row identity mismatch отклоняются до формирования passed evidence. |
| CHILD-22 | Native/external receipt audit | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и external harness receipt stores не проверялись без matching environments. |

Focused receipt audit result: `32/32` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 receipt lifecycle checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-23 | Explicit receipt transitions | `DONE / BOUNDED LOCAL` | Allowed prepared/terminal/rollback transitions are centralized and immutable. |
| CHILD-24 | Receipt identity binding | `DONE / BOUNDED LOCAL` | Request, policy, workspace-before и artifact-diff digests must remain identical across transitions. |
| CHILD-25 | Invalid transition rejection | `DONE / BOUNDED LOCAL` | Reuse across requests, artifact states и unsupported outcomes fail closed. |
| CHILD-26 | Native/external lifecycle transitions | `NOT_RUN / ENVIRONMENT-GATED` | Matching Windows/macOS и pinned external harness receipt histories не проверялись. |

Focused receipt lifecycle result: `33/33` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 receipt-chain checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-27 | Ordered receipt history | `DONE / BOUNDED LOCAL` | Chain validator проверяет каждый receipt и adjacent lifecycle transition, возвращает deterministic chain digest. |
| CHILD-28 | Gap/reorder/fork rejection | `DONE / BOUNDED LOCAL` | Lifecycle gaps, reordered outcomes и duplicate receipt IDs fail-closed. |
| CHILD-29 | Chain tamper rejection | `DONE / BOUNDED LOCAL` | Invalid signed fields/HMAC отклоняются до выпуска passed chain evidence. |
| CHILD-30 | Native/external receipt chains | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness receipt histories не проверялись. |

Focused receipt-chain result: `34/34` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 durable receipt-chain checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-31 | Durable ordered chain reopen | `DONE / BOUNDED LOCAL` | `audit_chain` загружает explicit receipt IDs из SQLite/WAL after reopen и возвращает deterministic chain result. |
| CHILD-32 | Reopen drift rejection | `DONE / BOUNDED LOCAL` | Reordering IDs и missing stored entries fail-closed; partial passed evidence не выпускается. |
| CHILD-33 | Append-only persistence | `DONE / BOUNDED LOCAL` | Audit только читает и проверяет receipts; chain gaps не repair-ятся автоматически. |
| CHILD-34 | Native/external durable chains | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness durable stores не проверялись. |

Focused durable chain result: `35/35` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 persistent chain snapshot checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-35 | Persistent chain snapshot | `DONE / BOUNDED LOCAL` | Ordered chain snapshot сохраняется с deterministic ID и idempotent duplicate semantics. |
| CHILD-36 | Snapshot reopen verification | `DONE / BOUNDED LOCAL` | Snapshot payload и current chain digest проверяются после SQLite/WAL reopen. |
| CHILD-37 | Snapshot drift/tamper rejection | `DONE / BOUNDED LOCAL` | Missing snapshot, malformed payload и current-chain drift fail-closed. |
| CHILD-38 | Native/external snapshots | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness snapshot stores не проверялись. |

Focused snapshot result: `36/36` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 snapshot-to-recovery link checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-39 | Snapshot-bound recovery action | `DONE / BOUNDED LOCAL` | Recovery action fingerprint включает `chain_snapshot_id`; target receipt membership проверяется до handler. |
| CHILD-40 | Stale snapshot rejection | `DONE / BOUNDED LOCAL` | Missing, corrupted и unrelated snapshots fail-closed; silent rebinding запрещён. |
| CHILD-41 | Completion linkage | `DONE / BOUNDED LOCAL` | Successful recovery event сохраняет snapshot ID и snapshot digest. |
| CHILD-42 | Native/external recovery linkage | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness recovery snapshots не проверялись. |

Focused snapshot-recovery result: `37/37` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 recovery completion receipt checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-43 | Signed recovery completion receipt | `DONE / BOUNDED LOCAL` | Successful recovery creates committed signed receipt bound to action, run, scope, operator and optional snapshot. |
| CHILD-44 | Replay receipt verification | `DONE / BOUNDED LOCAL` | Exact replay validates referenced completion receipt before returning `replayed`. |
| CHILD-45 | Event tamper rejection | `DONE / BOUNDED LOCAL` | Tampered completion receipt reference fails closed; action payload replay conflict remains enforced. |
| CHILD-46 | Native/external completion receipts | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness completion receipts не проверялись. |

Focused completion receipt result: `38/38` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 recovery completion-event chain checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-47 | Hash-linked completion events | `DONE / BOUNDED LOCAL` | Новые completion events содержат previous-event digest от `genesis` до current head. |
| CHILD-48 | Event-chain audit | `DONE / BOUNDED LOCAL` | Audit проверяет order, unique action IDs, linked digests и committed completion receipts. |
| CHILD-49 | Event reorder/corruption rejection | `DONE / BOUNDED LOCAL` | Reorder, fork, malformed payload и missing receipt fail-closed. |
| CHILD-50 | Native/external event chains | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness event chains не проверялись. |

Focused event-chain result: `39/39` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 durable event-chain snapshot checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-51 | Signed event-chain snapshot | `DONE / BOUNDED LOCAL` | После completion event создаётся HMAC-signed sidecar snapshot через atomic replace. |
| CHILD-52 | Snapshot reopen verification | `DONE / BOUNDED LOCAL` | Reopen проверяет signature, event IDs, receipt IDs, count и chain digest. |
| CHILD-53 | Snapshot drift/tamper rejection | `DONE / BOUNDED LOCAL` | Sidecar tampering и stale snapshot против нового/reordered event log fail-closed. |
| CHILD-54 | Native/external event snapshots | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness event snapshots не проверялись. |

Focused durable snapshot result: `39/39` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 recovery evidence startup checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-55 | Startup/replay evidence gate | `DONE / BOUNDED LOCAL` | `verify_recovery_evidence()` audit-ит event chain и snapshot как explicit startup/replay check. |
| CHILD-56 | Missing snapshot honesty | `DONE / BOUNDED LOCAL` | Non-empty event log без snapshot fail-closed; empty log остаётся `not_run` no-op. |
| CHILD-57 | Snapshot replay integrity | `DONE / BOUNDED LOCAL` | Reopen проверяет HMAC, IDs, receipts, count и chain digest без automatic repair. |
| CHILD-58 | Native/external startup gates | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness startup verification не проверялись. |

Focused startup/replay result: `40/40` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 recovery evidence status checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-59 | Evidence status projection | `DONE / BOUNDED LOCAL` | Добавлен machine-readable status с schema version, claim flag и deterministic reason. |
| CHILD-60 | Status honesty | `DONE / BOUNDED LOCAL` | Valid evidence = `passed/true`; empty log = `not_run/false`; missing/stale/corrupt evidence = `blocked/false`. |
| CHILD-61 | Boundary preservation | `DONE / BOUNDED LOCAL` | Projection read-only; blocked не превращается в not_run и ни один external lane не становится passed по implication. |
| CHILD-62 | Native/external status projection | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness status evidence не проверялись. |

Focused status result: `41/41` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 recovery status snapshot checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-63 | Signed status snapshot | `DONE / BOUNDED LOCAL` | После completion сохраняется signed status sidecar с status, claim, reason и chain digest. |
| CHILD-64 | Status snapshot reopen | `DONE / BOUNDED LOCAL` | Reopen проверяет HMAC и сравнивает projection с current recovery evidence. |
| CHILD-65 | Status snapshot tamper/drift | `DONE / BOUNDED LOCAL` | Tampered sidecar и drift underlying event/snapshot state fail-closed. |
| CHILD-66 | Native/external status snapshots | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness status snapshots не проверялись. |

Focused status snapshot result: `42/42` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 status-snapshot replay checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-67 | Replay status binding | `DONE / BOUNDED LOCAL` | Exact replay проверяет action fingerprint, committed completion receipt и signed status snapshot. |
| CHILD-68 | Missing replay snapshot | `DONE / BOUNDED LOCAL` | Missing status sidecar fail-closed с `recovery_status_snapshot_missing`; automatic recreation запрещена. |
| CHILD-69 | Stale replay projection | `DONE / BOUNDED LOCAL` | Stale/corrupted status snapshot не возвращает `replayed`. |
| CHILD-70 | Native/external replay status | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness replay status не проверялись. |

Focused replay result: `43/43` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 replay outcome evidence checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-71 | Replay evidence schema | `DONE / BOUNDED LOCAL` | `audit_replay_outcome()` выпускает read-only `noesis.recovery-replay-evidence.v1` с action, receipt и status-snapshot digests. |
| CHILD-72 | Replay claim honesty | `DONE / BOUNDED LOCAL` | `claim=true` только после полной проверки immutable evidence set. |
| CHILD-73 | Replay outcome tamper | `DONE / BOUNDED LOCAL` | Missing, stale, corrupt или mismatched evidence fail-closed без side effects. |
| CHILD-74 | Native/external replay evidence | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness replay outcome evidence не проверялись. |

Focused replay outcome result: `43/43` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-20 — Gate 3 durable replay outcome snapshot checkpoint

| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-75 | Durable replay snapshot | `DONE / BOUNDED LOCAL` | После confirmed recovery completion сохраняется signed `noesis.recovery-replay-evidence-snapshot.v1` sidecar через atomic replace. |
| CHILD-76 | Replay snapshot verification | `DONE / BOUNDED LOCAL` | Exact replay проверяет sidecar против action, committed receipt и status snapshot до возврата `replayed`. |
| CHILD-77 | Replay snapshot tamper | `DONE / BOUNDED LOCAL` | Missing, signature tamper и evidence drift fail-closed без side effects. |
| CHILD-78 | Native/external replay snapshots | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness replay snapshots не проверялись. |

Focused replay snapshot result: `45/45` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.
## 2026-08-20 — Gate 3 replay snapshot inventory audit checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-79 | Deterministic replay snapshot inventory | `DONE / BOUNDED LOCAL` | `audit_replay_snapshot_inventory()` выпускает read-only `noesis.recovery-replay-snapshot-inventory.v1` с verified path, payload digest, action identity и completion receipt identity. |
| CHILD-80 | Inventory repeatability | `DONE / BOUNDED LOCAL` | Повторный audit неизменённого sidecar даёт byte-equivalent projection; verification failure не создаёт partial inventory. |
| CHILD-81 | Native/external inventory | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness inventory audits не проверялись. |
Focused replay inventory result: `45/45` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 replay inventory adversarial closure checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-82 | Signed snapshot path binding | `DONE / BOUNDED LOCAL` | Replay snapshot подписывает canonical sidecar path; signed path mismatch fail-closed с `recovery_replay_snapshot_path_mismatch`. |
| CHILD-83 | Duplicate/conflicting snapshot records | `DONE / BOUNDED LOCAL` | Duplicate JSON keys rejected as `recovery_replay_snapshot_duplicate_record`; no partial inventory is emitted. |
| CHILD-84 | Replay identity confusion | `DONE / BOUNDED LOCAL` | Signed action ID/digest or completion receipt mismatch rejected with `recovery_replay_snapshot_identity_conflict`. |
| CHILD-85 | Native/external adversarial inventory | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness inventory adversarial lanes не запускались. |
Focused adversarial result: `48/48` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 durable replay inventory snapshot checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-86 | Durable inventory snapshot | `DONE / BOUNDED LOCAL` | После replay snapshot сохраняется signed `noesis.recovery-replay-snapshot-inventory-snapshot.v1` sidecar через atomic replace. |
| CHILD-87 | Inventory snapshot reopen | `DONE / BOUNDED LOCAL` | Exact replay и explicit verifier сравнивают durable inventory snapshot с current replay snapshot до возврата `replayed`. |
| CHILD-88 | Inventory snapshot recovery denial | `DONE / BOUNDED LOCAL` | Missing, corrupt, signed path mismatch и evidence drift fail-closed; automatic recreation во время replay запрещена. |
| CHILD-89 | Native/external inventory snapshots | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness inventory snapshots не проверялись. |
Focused durable inventory result: `51/51` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 action-scoped replay evidence checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-90 | Action-scoped replay sidecars | `DONE / BOUNDED LOCAL` | Replay и inventory sidecars используют deterministic `action_id` digest in filename; same event log no longer shares one mutable replay sidecar across actions. |
| CHILD-91 | Action-scoped recovery status | `DONE / BOUNDED LOCAL` | Replay verifies action-scoped signed status projection while global operator status remains separate. |
| CHILD-92 | Multi-action replay isolation | `DONE / BOUNDED LOCAL` | Two completed actions preserve independent replay/inventory/status sidecars and both exact replays return `replayed`. |
| CHILD-93 | Native/external action-scoped evidence | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness multi-action replay evidence не проверялись. |
Focused action-scoped result: `51/51` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 replay evidence catalog checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-94 | Global replay evidence catalog | `DONE / BOUNDED LOCAL` | `audit_replay_evidence_catalog()` выпускает read-only `noesis.recovery-replay-evidence-catalog.v1` с deterministic catalog digest. |
| CHILD-95 | Cross-artifact binding | `DONE / BOUNDED LOCAL` | Каждый inventory record связывается с action-scoped replay snapshot, action event, committed completion receipt и action-scoped status snapshot. |
| CHILD-96 | Catalog fail-closed audit | `DONE / BOUNDED LOCAL` | Missing, duplicate, stale, path-conflicting, signature-invalid и identity-conflicting records отклоняются; exact replay запускает catalog audit. |
| CHILD-97 | Native/external replay catalog | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness catalog audits не проверялись. |
Focused catalog result: `52/52` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 durable replay catalog snapshot checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-98 | Durable catalog snapshot | `DONE / BOUNDED LOCAL` | После catalog audit сохраняется signed `noesis.recovery-replay-evidence-catalog-snapshot.v1` sidecar через atomic replace. |
| CHILD-99 | Catalog snapshot reopen | `DONE / BOUNDED LOCAL` | Exact replay проверяет durable global catalog snapshot против current catalog до возврата `replayed`. |
| CHILD-100 | Catalog snapshot recovery denial | `DONE / BOUNDED LOCAL` | Missing, corrupt, signed path mismatch и catalog drift fail-closed; automatic recreation during replay запрещена. |
| CHILD-101 | Native/external catalog snapshots | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness durable catalog snapshots не проверялись. |
Focused durable catalog result: `55/55` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 replay evidence commit manifest checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-102 | Signed commit manifest | `DONE / BOUNDED LOCAL` | Для каждой action сохраняется signed `noesis.recovery-replay-evidence-commit-manifest.v1`, связывающий committed receipt и все replay evidence sidecars. |
| CHILD-103 | Last-write verification | `DONE / BOUNDED LOCAL` | Exact replay проверяет commit manifest последним, после status/replay/inventory/catalog verification. |
| CHILD-104 | Partial-bundle denial | `DONE / BOUNDED LOCAL` | Missing, corrupt, signed path mismatch и manifest digest drift fail-closed; automatic repair запрещён. |
| CHILD-105 | Native/external commit manifests | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness commit manifests не проверялись. |
Focused manifest result: `58/58` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 replay evidence completeness checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-106 | Completeness schema | `DONE / BOUNDED LOCAL` | `audit_replay_evidence_completeness()` выпускает read-only `noesis.recovery-replay-evidence-completeness.v1`. |
| CHILD-107 | One manifest per completion | `DONE / BOUNDED LOCAL` | Каждый completed recovery event обязан иметь exactly one valid action-scoped signed commit manifest. |
| CHILD-108 | Count parity and receipt binding | `DONE / BOUNDED LOCAL` | Event count, manifest count и catalog count обязаны совпадать; completion receipt identity проверяется against durable receipt store. |
| CHILD-109 | Native/external completeness | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness completeness audits не проверялись. |
Focused completeness result: `59/59` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 durable replay completeness snapshot checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-110 | Durable completeness snapshot | `DONE / BOUNDED LOCAL` | Completeness claim сохраняется signed `noesis.recovery-replay-evidence-completeness-snapshot.v1` sidecar через atomic replace. |
| CHILD-111 | Completeness snapshot reopen | `DONE / BOUNDED LOCAL` | Exact replay проверяет durable completeness snapshot после commit manifest gate и до возврата `replayed`. |
| CHILD-112 | Completeness snapshot recovery denial | `DONE / BOUNDED LOCAL` | Missing, corrupt, signed path mismatch и completeness drift fail-closed; automatic recreation during replay запрещена. |
| CHILD-113 | Native/external completeness snapshots | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness completeness snapshots не проверялись. |
Focused durable completeness result: `62/62` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 commit-manifest finality checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-114 | Provisional-to-final transition | `DONE / BOUNDED LOCAL` | New action сначала получает provisional manifest, затем completeness snapshot и final atomic manifest rewrite; multi-action update не ломает replay. |
| CHILD-115 | Stable completeness binding | `DONE / BOUNDED LOCAL` | Manifest связывается с stable per-action completeness-record digest, а не с mutable aggregate completeness digest. |
| CHILD-116 | Final write ordering | `DONE / BOUNDED LOCAL` | Exact replay требует final manifest после current completeness snapshot verification. |
| CHILD-117 | Native/external finality | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness finality transitions не проверялись. |
Focused finality result: `62/62` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 mandatory completion-chain replay checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-118 | Exact chain snapshot gate | `DONE / BOUNDED LOCAL` | Exact replay сначала проверяет signed `noesis.recovery-event-chain-snapshot.v1` против append-only completion events. |
| CHILD-119 | Direct denial ordering | `DONE / BOUNDED LOCAL` | Missing/drifted chain snapshot выдаёт direct `recovery_event_snapshot_*` denial до status projection checks. |
| CHILD-120 | Duplicate chain snapshot records | `DONE / BOUNDED LOCAL` | Duplicate JSON keys в completion-chain snapshot fail-closed. |
| CHILD-121 | Native/external chain replay | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness completion-chain replay не проверялись. |
Focused chain replay result: `64/64` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 replay-to-event receipt binding checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-122 | Target event prefix | `DONE / BOUNDED LOCAL` | Replay projection audits completion-event prefix for target action before producing signed replay evidence. |
| CHILD-123 | Receipt identity binding | `DONE / BOUNDED LOCAL` | Final committed receipt ID in target event must equal replay record completion receipt ID. |
| CHILD-124 | Event chain digest projection | `DONE / BOUNDED LOCAL` | Signed replay evidence includes target `event_chain_digest`; replay snapshot verification rechecks it deterministically. |
| CHILD-125 | Native/external receipt binding | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness receipt-to-event replay binding не проверялись. |
Focused receipt-binding result: `64/64` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 deterministic evidence bundle digest checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-126 | Canonical bundle digest | `DONE / BOUNDED LOCAL` | Final commit manifest содержит deterministic `bundle_digest` по canonical action-scoped fields. |
| CHILD-127 | Whole-bundle verification | `DONE / BOUNDED LOCAL` | Verification пересчитывает digest и связывает status/replay/inventory/catalog/completeness/receipt/path projections. |
| CHILD-128 | Bundle tamper denial | `DONE / BOUNDED LOCAL` | Изменение bundle digest или любого покрытого поля блокирует final manifest verification. |
| CHILD-129 | Native/external bundle digest | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness whole-bundle digest не проверялись. |
Focused bundle-digest result: `64/64` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 startup completeness bundle-digest checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-130 | Startup digest verification | `DONE / BOUNDED LOCAL` | `audit_replay_evidence_completeness()` independently recomputes each signed manifest `bundle_digest`. |
| CHILD-131 | Count-parity tamper denial | `DONE / BOUNDED LOCAL` | Bundle digest denial occurs before startup completeness claim and count-parity acceptance. |
| CHILD-132 | Direct manifest denial ordering | `DONE / BOUNDED LOCAL` | Exact manifest drift reports `recovery_replay_commit_manifest_drift` before aggregate completeness drift. |
| CHILD-133 | Native/external startup digest | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness startup completeness digest не проверялись. |
Focused startup completeness result: `65/65` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 startup partial-bundle path checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-134 | Referenced path completeness | `DONE / BOUNDED LOCAL` | Startup audit требует existence и canonical binding для event/status/replay/inventory/catalog/completeness paths. |
| CHILD-135 | Partial-bundle denial | `DONE / BOUNDED LOCAL` | Missing action evidence path блокирует completeness claim с `recovery_replay_completeness_bundle_path_missing`. |
| CHILD-136 | Bootstrap exception | `DONE / BOUNDED LOCAL` | Только собственный completeness snapshot может отсутствовать до его first atomic bootstrap write. |
| CHILD-137 | Native/external path completeness | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness partial-bundle path audits не проверялись. |
Focused partial-bundle result: `66/66` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 startup sidecar signature checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-138 | Sidecar signature verification | `DONE / BOUNDED LOCAL` | Startup completeness audit проверяет signatures для referenced status/replay/inventory/catalog/completeness sidecars. |
| CHILD-139 | Sidecar duplicate-key denial | `DONE / BOUNDED LOCAL` | Duplicate JSON keys в referenced sidecar fail-closed с `recovery_replay_completeness_sidecar_duplicate_record`. |
| CHILD-140 | Sidecar corruption denial | `DONE / BOUNDED LOCAL` | Corrupt или invalid signature блокируют completeness claim до count parity. |
| CHILD-141 | Native/external sidecar integrity | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness sidecar integrity не проверялись. |
Focused sidecar-integrity result: `67/67` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 startup sidecar binding checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-142 | Action identity binding | `DONE / BOUNDED LOCAL` | Startup audit сравнивает action IDs status/replay/inventory sidecars с manifest action identity. |
| CHILD-143 | Sidecar digest binding | `DONE / BOUNDED LOCAL` | Status/replay/inventory payload digests сравниваются с manifest digest fields. |
| CHILD-144 | Cross-action/stale denial | `DONE / BOUNDED LOCAL` | Valid signature с другой action identity или stale content блокирует completeness claim. |
| CHILD-145 | Native/external sidecar binding | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness sidecar binding не проверялись. |
Focused sidecar-binding result: `68/68` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.
## 2026-08-20 — Gate 3 startup catalog binding checkpoint
| ID | Gate | Статус | Evidence |
|---|---|---|---|
| CHILD-146 | Durable catalog snapshot verification | `DONE / BOUNDED LOCAL` | Startup completeness повторно проверяет signed global catalog snapshot против current inventory projection. |
| CHILD-147 | Per-action catalog record binding | `DONE / BOUNDED LOCAL` | Каждый manifest `catalog_record_digest` сравнивается с immutable record соответствующей action. |
| CHILD-148 | Catalog drift denial | `DONE / BOUNDED LOCAL` | Signed catalog snapshot drift блокирует startup completeness до count parity acceptance. |
| CHILD-149 | Native/external catalog binding | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness catalog binding не проверялись. |
Focused catalog-binding result: `69/69` assurance, recovery, child-runtime и export tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full-suite validation pending.


## 2026-08-21 — Gate 3 startup durable completeness snapshot checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-150 | Durable completeness snapshot requirement | `DONE / BOUNDED LOCAL` | `audit_replay_evidence_completeness(require_durable_snapshot=True)` требует существующий signed `noesis.recovery-replay-evidence-completeness-snapshot.v1` в startup/exact-replay path. |
| CHILD-151 | Completeness digest binding | `DONE / BOUNDED LOCAL` | Durable snapshot содержит deterministic `completeness_digest`, а verification сравнивает его с текущими ordered records и verified catalog digest. |
| CHILD-152 | Stale snapshot denial | `DONE / BOUNDED LOCAL` | Signed stale `completeness_digest` блокирует startup audit с `recovery_replay_completeness_snapshot_drift`. |
| CHILD-153 | Missing durable snapshot denial | `DONE / BOUNDED LOCAL` | Startup audit не принимает заново вычисленную in-memory completeness projection без durable snapshot; причина `recovery_replay_completeness_snapshot_required`. |
| CHILD-154 | Native/external completeness snapshot | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness durable completeness snapshot binding не проверялись. |

Focused completeness-binding result: `40/40` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression result: `734/734` passed in `53.118 s`; documentation, security и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 completeness snapshot schema-validation checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-155 | Snapshot schema/status validation | `DONE / BOUNDED LOCAL` | Verifier требует exact snapshot schema `noesis.recovery-replay-evidence-completeness-snapshot.v1` и `status=passed` до digest comparison. |
| CHILD-156 | Count and record-shape validation | `DONE / BOUNDED LOCAL` | Event/manifest/catalog counts должны быть non-negative integers; records — list of mappings с unique action IDs и согласованным manifest count. |
| CHILD-157 | Malformed and duplicate-key denial | `DONE / BOUNDED LOCAL` | Malformed records, duplicate action IDs и duplicate JSON keys fail-closed с explicit deterministic reasons. |
| CHILD-158 | Native/external schema validation | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness completeness snapshot schema validation не проверялись. |

Focused schema-validation result: `43/43` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 canonical completeness field-set checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-159 | Canonical outer field set | `DONE / BOUNDED LOCAL` | Completeness snapshot verifier отклоняет unknown и missing outer payload fields до digest comparison. |
| CHILD-160 | Canonical per-action record set | `DONE / BOUNDED LOCAL` | Каждый record обязан иметь ровно canonical fields `action_id`, `manifest_path`, `action_digest`, `completion_receipt_id`, `catalog_record_digest`. |
| CHILD-161 | Unknown-field adversarial denial | `DONE / BOUNDED LOCAL` | Signed payload с extra field и signed per-action record с extra field fail-closed с explicit schema reasons. |
| CHILD-162 | Native/external canonical schema | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness canonical completeness field-set validation не проверялись. |

Focused canonical-field result: `45/45` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 completeness snapshot deterministic-reopen checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-163 | Byte identity | `DONE / BOUNDED LOCAL` | Повторная persistence неизменённого completeness snapshot даёт byte-identical JSON bytes и identical signed payload. |
| CHILD-164 | Same-process reopen | `DONE / BOUNDED LOCAL` | Fresh `ExecutionRecoveryExecutor` reopen-ит и verify-ит durable completeness snapshot без regeneration. |
| CHILD-165 | Python process-boundary reopen | `DONE / BOUNDED LOCAL` | Отдельный Python 3.14 process успешно verify-ит существующий snapshot; stdout `passed`, stderr пустой. |
| CHILD-166 | Native/external deterministic reopen | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness process-boundary reopen evidence не проверялись. |

Focused deterministic-reopen result: `47/47` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 completeness snapshot interrupted-write checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-167 | Interrupted replacement | `DONE / BOUNDED LOCAL` | Simulated `os.replace` interruption оставляет предыдущий canonical snapshot неизменённым и valid после reopen. |
| CHILD-168 | Temporary cleanup | `DONE / BOUNDED LOCAL` | Atomic writer удаляет свой temporary file после interrupted replacement; orphan partial file не входит в accepted evidence path. |
| CHILD-169 | No silent temp promotion | `DONE / BOUNDED LOCAL` | При missing canonical snapshot orphan partial temporary file не используется; verifier fail-closed с `recovery_replay_completeness_snapshot_missing`. |
| CHILD-170 | Native/external interrupted write | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness interruption/reopen behavior не проверялись. |

Focused interrupted-write result: `49/49` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 multi-action completeness crash-boundary checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-171 | Stale prior snapshot denial | `DONE / BOUNDED LOCAL` | После append второго completion event старый one-action completeness snapshot получает `recovery_replay_completeness_snapshot_drift` и не принимается для replay. |
| CHILD-172 | Explicit finalization recovery | `DONE / BOUNDED LOCAL` | После simulated crash explicit completeness write и final manifest write восстанавливают valid multi-action evidence без silent repair. |
| CHILD-173 | Full-catalog deterministic recovery | `DONE / BOUNDED LOCAL` | Recovered snapshot содержит `manifest_count=2`, `catalog_count=2`; повторная persistence byte-identical; exact replay второй action проходит. |
| CHILD-174 | Native/external multi-action recovery | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness multi-action crash recovery не проверялись. |

Focused multi-action result: `50/50` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 multi-action manifest-corruption checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-175 | Signed manifest corruption denial | `DONE / BOUNDED LOCAL` | Signed-but-wrong action digest в одном manifest вызывает `recovery_replay_completeness_identity_conflict`. |
| CHILD-176 | No partial pass | `DONE / BOUNDED LOCAL` | Startup completeness не выдаёт partial `passed`; весь multi-action bundle отклоняется до восстановления corrupted manifest. |
| CHILD-177 | Trusted explicit repair | `DONE / BOUNDED LOCAL` | После explicit restoration trusted signed manifest audit снова принимает обе action; verifier не реконструирует bundle из untrusted current state. |
| CHILD-178 | Deterministic repair finalization | `DONE / BOUNDED LOCAL` | Повторная final manifest persistence byte-identical; completeness `manifest_count=2` и durable replay verification проходят. |
| CHILD-179 | Native/external manifest repair | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness manifest corruption/repair не проверялись. |

Focused manifest-corruption result: `51/51` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 global catalog-corruption checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-180 | Signed catalog corruption denial | `DONE / BOUNDED LOCAL` | Signed catalog snapshot с extra record и drifted count вызывает `recovery_replay_catalog_snapshot_drift`. |
| CHILD-181 | No partial catalog parity | `DONE / BOUNDED LOCAL` | Multi-action completeness audit блокируется до count parity; corrupted global catalog не даёт partial `catalog_count`. |
| CHILD-182 | Trusted catalog restoration | `DONE / BOUNDED LOCAL` | После explicit restoration trusted catalog snapshot `verify_replay_evidence_catalog_snapshot()` снова проходит. |
| CHILD-183 | Deterministic catalog finalization | `DONE / BOUNDED LOCAL` | Repeated catalog persistence byte-identical; restored completeness `catalog_count=2` и durable snapshot verification проходят. |
| CHILD-184 | Native/external catalog recovery | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness global catalog corruption/repair не проверялись. |

Focused catalog-corruption result: `52/52` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 catalog-record cross-binding checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-185 | Per-action record digest binding | `DONE / BOUNDED LOCAL` | Commit manifest каждого action связывает exact `catalog_record_digest` immutable catalog record. |
| CHILD-186 | Signed substitution denial | `DONE / BOUNDED LOCAL` | Validly signed manifest с digest record другого action отклоняется как `recovery_replay_completeness_catalog_record_mismatch`. |
| CHILD-187 | Cross-binding restoration | `DONE / BOUNDED LOCAL` | После trusted restoration original manifest digest binding снова принимает обе action. |
| CHILD-188 | Deterministic repaired manifest | `DONE / BOUNDED LOCAL` | Repeated repaired manifest persistence byte-identical; final commit-manifest verification проходит. |
| CHILD-189 | Native/external record binding | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness per-action catalog binding не проверялись. |

Focused catalog-record binding result: `53/53` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 duplicate-identity checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-190 | Duplicate catalog action ID | `DONE / BOUNDED LOCAL` | Signed catalog с duplicate action record отклоняется с `recovery_replay_catalog_snapshot_duplicate_action` до count parity. |
| CHILD-191 | Duplicate completeness action ID | `DONE / BOUNDED LOCAL` | Signed completeness snapshot с duplicate action record отклоняется с `recovery_replay_completeness_snapshot_duplicate_action`. |
| CHILD-192 | Trusted clean restoration | `DONE / BOUNDED LOCAL` | После explicit removal duplicate identity catalog и completeness verification снова проходят с `manifest_count=2`. |
| CHILD-193 | Deterministic clean rebuild | `DONE / BOUNDED LOCAL` | Повторная clean catalog и completeness persistence byte-identical. |
| CHILD-194 | Native/external duplicate identity | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness duplicate identity recovery не проверялись. |

Focused duplicate-identity result: `54/54` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 strict manifest discovery checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-195 | Orphan manifest denial | `DONE / BOUNDED LOCAL` | Unknown/orphan manifest filename отклоняется до parsing с `recovery_replay_completeness_orphan_manifest`. |
| CHILD-196 | Canonical path collision | `DONE / BOUNDED LOCAL` | Если две expected actions отображаются в один canonical manifest path, audit fail-closed с `recovery_replay_completeness_manifest_path_collision`. |
| CHILD-197 | No pre-parity parsing | `DONE / BOUNDED LOCAL` | Orphan `not-json` файл отклоняется по filename discovery, не маскируясь как corrupt/partial accepted record. |
| CHILD-198 | Clean restoration | `DONE / BOUNDED LOCAL` | После удаления orphan manifest и восстановления canonical mapping completeness count снова проходит. |
| CHILD-199 | Native/external manifest discovery | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness unknown/orphan manifest discovery не проверялись. |

Focused manifest-discovery result: `56/56` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 strict sidecar-binding checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-200 | Orphan sidecar denial | `DONE / BOUNDED LOCAL` | Extra `.status` sidecar filename отклоняется с `recovery_replay_completeness_orphan_sidecar` до sidecar parsing. |
| CHILD-201 | Canonical sidecar alias denial | `DONE / BOUNDED LOCAL` | Symlink вместо canonical action status path отклоняется с `recovery_replay_completeness_sidecar_alias`. |
| CHILD-202 | Sidecar allowlist | `DONE / BOUNDED LOCAL` | Strict expected set охватывает event, status, replay, inventory, catalog, completeness и commit-manifest artifacts. |
| CHILD-203 | Clean sidecar restoration | `DONE / BOUNDED LOCAL` | После удаления orphan и восстановления regular canonical file completeness count снова проходит. |
| CHILD-204 | Native/external sidecar binding | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness sidecar alias/orphan discovery не проверялись. |

Focused sidecar-binding result: `58/58` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 path-containment checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-205 | Path containment | `DONE / BOUNDED LOCAL` | Canonical evidence paths проверяются через realpath/commonpath внутри expected event directory. |
| CHILD-206 | Manifest file identity | `DONE / BOUNDED LOCAL` | Manifest symlink и multi-link manifest отклоняются до payload acceptance. |
| CHILD-207 | Sidecar file identity | `DONE / BOUNDED LOCAL` | External hardlink status sidecar отклоняется с `recovery_replay_completeness_sidecar_file_identity`. |
| CHILD-208 | Trusted regular-file restoration | `DONE / BOUNDED LOCAL` | После восстановления независимого regular status file completeness count снова проходит. |
| CHILD-209 | Native/external path identity | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness hardlink/path identity не проверялись. |

Focused path-containment result: `59/59` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 crash-consistency checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-210 | Mixed generation denial | `DONE / BOUNDED LOCAL` | Новый signed status sidecar рядом со старым manifest отклоняется по `recovery_replay_completeness_sidecar_digest_mismatch`. |
| CHILD-211 | Old complete generation | `DONE / BOUNDED LOCAL` | После восстановления исходного sidecar старая complete generation снова проходит без regeneration. |
| CHILD-212 | Explicit full rebuild boundary | `DONE / BOUNDED LOCAL` | Повреждённая старая generation не silently repaired; acceptance требует explicit rebuild всех bundle members. |
| CHILD-213 | Generation-bound finalization contract | `DONE / BOUNDED LOCAL` | Atomic per-file replacement не превращает mixed old/new evidence в `passed`. |
| CHILD-214 | Native/external crash consistency | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness simultaneous finalization не проверялись. |

Focused crash-consistency result: `60/60` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 generation-receipt checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-215 | Generation receipt schema | `DONE / BOUNDED LOCAL` | Signed `noesis.recovery-replay-generation-receipt.v1` содержит canonical file inventory и `generation_digest`. |
| CHILD-216 | Whole-generation binding | `DONE / BOUNDED LOCAL` | Startup проверяет receipt после per-artifact checks; изменённый file inventory или digest блокирует generation целиком. |
| CHILD-217 | Receipt drift/missing denial | `DONE / BOUNDED LOCAL` | Signed stale digest вызывает `recovery_replay_generation_receipt_drift`; missing receipt вызывает `recovery_replay_generation_receipt_missing`. |
| CHILD-218 | Deterministic receipt persistence | `DONE / BOUNDED LOCAL` | Повторная запись unchanged generation receipt byte-identical; trusted rebuild восстанавливает pass. |
| CHILD-219 | Native/external generation receipt | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness generation receipt не проверялись. |

Focused generation-receipt result: `61/61` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 generation-receipt schema checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-220 | Canonical receipt fields | `DONE / BOUNDED LOCAL` | Outer generation receipt и file records используют exact immutable field sets. |
| CHILD-221 | Receipt schema denial | `DONE / BOUNDED LOCAL` | Unknown/missing fields и stale schema version fail-closed до digest comparison. |
| CHILD-222 | Receipt path/file identity | `DONE / BOUNDED LOCAL` | Non-canonical path, symlink, hardlink, duplicate file identity и invalid SHA-256 отклоняются. |
| CHILD-223 | Process-boundary reopen | `DONE / BOUNDED LOCAL` | Отдельный Python 3.14 process verify-ит signed generation receipt без regeneration. |
| CHILD-224 | Multi-action receipt rotation | `DONE / BOUNDED LOCAL` | Receipt deterministic обновляется после multi-action finalization и восстанавливается только через trusted rebuild. |
| CHILD-225 | Native/external receipt schema | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness receipt rotation не проверялись. |

Focused generation-schema result: `62/62` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 receipt-rotation checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-226 | Monotonic generation ID | `DONE / BOUNDED LOCAL` | Receipt содержит положительный `generation_id`, вычисленный по append-only completed-event count и включённый в generation digest. |
| CHILD-227 | Stale receipt denial | `DONE / BOUNDED LOCAL` | Receipt generation 1 отклоняется после multi-action append, когда current generation равна 2. |
| CHILD-228 | Multi-action rotation | `DONE / BOUNDED LOCAL` | Rotation 1→2 проходит только с полным file inventory и final manifest set; generation digest меняется deterministic. |
| CHILD-229 | Receipt/final-manifest crash boundary | `DONE / BOUNDED LOCAL` | Interrupted mixed transition не даёт partial `passed`; требуется complete trusted generation rebuild. |
| CHILD-230 | Native/external rotation | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness receipt rotation не проверялись. |

Focused rotation result: `63/63` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 old-prefix binding checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-231 | Event-chain binding | `DONE / BOUNDED LOCAL` | Generation receipt связывает current `event_chain_digest` с append-only completion event prefix. |
| CHILD-232 | Completeness binding | `DONE / BOUNDED LOCAL` | Generation receipt связывает current `completeness_digest`; старое значение с valid signature fail-closed. |
| CHILD-233 | Old-prefix denial | `DONE / BOUNDED LOCAL` | Receipt старого event prefix не может быть promoted как current generation через replay/rollback. |
| CHILD-234 | Native/external prefix replay | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness old-prefix replay не проверялись. |

Focused old-prefix cross-binding result: `63/63` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 event-chain repair checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-235 | Chain reorder denial | `DONE / BOUNDED LOCAL` | Reordered completion events отклоняются с chain mismatch до generation receipt verification. |
| CHILD-236 | Chain duplicate/fork denial | `DONE / BOUNDED LOCAL` | Duplicate action event отклоняется как `recovery_completion_event_fork`; receipt не маскирует fork. |
| CHILD-237 | Trusted append-only repair | `DONE / BOUNDED LOCAL` | После восстановления исходного event order и unique identities current generation receipt снова проходит deterministic verification. |
| CHILD-238 | Native/external chain repair | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness event-chain repair не проверялись. |

Focused event-chain result: `63/63` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 event-chain snapshot rotation checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-239 | Chain snapshot schema | `DONE / BOUNDED LOCAL` | Exact field set, schema version, count/list parity, unique event IDs и non-empty digest проверяются до drift comparison. |
| CHILD-240 | Chain snapshot denial | `DONE / BOUNDED LOCAL` | Unknown/missing fields, invalid shape, stale schema, duplicate keys и missing snapshot fail-closed. |
| CHILD-241 | Chain snapshot reopen | `DONE / BOUNDED LOCAL` | Отдельный Python process reopen/verify-ит signed chain snapshot без regeneration. |
| CHILD-242 | Native/external chain snapshot | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness chain snapshot rotation не проверялись. |

Focused event-snapshot result: `64/64` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 cross-artifact chain-root checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-243 | Generation/global chain binding | `DONE / BOUNDED LOCAL` | Generation receipt связывает current global `event_chain_digest` с signed event-chain snapshot. |
| CHILD-244 | Final manifest/action chain binding | `DONE / BOUNDED LOCAL` | Final commit manifest содержит exact `replay_event_chain_digest` для action prefix. |
| CHILD-245 | Chain-root substitution denial | `DONE / BOUNDED LOCAL` | Validly signed manifest со старым-prefix chain digest fail-closed до completeness acceptance. |
| CHILD-246 | Native/external chain root | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и pinned external harness cross-artifact chain root не проверялись. |

Focused chain-root result: `65/65` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`; full regression и release audits должны быть подтверждены перед commit.


## 2026-08-21 — Gate 3 explicit replay finalization checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-247 | Explicit replay promotion | `DONE / BOUNDED LOCAL` | `promote_replay_evidence_finalization()` требует durable completeness и passed generation receipt, затем atomic пишет signed finalization marker. |
| CHILD-248 | OS-level immutability | `DONE / BOUNDED LOCAL` | Generation files, generation receipt и finalization marker переводятся в read-only mode; fresh executor verifies без regeneration. |
| CHILD-249 | Interrupted promotion recovery | `DONE / BOUNDED LOCAL` | Marker-last protocol и partial permission failure fail-closed как `recovery_replay_finalization_partial` / `not_immutable`. |
| CHILD-250 | Post-finalization mutation denial | `DONE / BOUNDED LOCAL` | Все replay evidence writers отвергают последующую запись с `recovery_replay_finalization_immutable`; altered artifact вызывает generation drift. |
| CHILD-251 | Native/external finalization | `NOT_RUN / ENVIRONMENT-GATED` | Windows/macOS filesystem semantics и external harness finalization не запускались. |

Focused finalization result: `68/68` execution-recovery tests passed; full suite `762/762` passed on Python 3.14.7 with tracemalloc and `-W error::ResourceWarning`.


## 2026-08-21 — Gate 3 strict finalized-readiness checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-252 | Startup replay readiness API | `DONE / BOUNDED LOCAL` | `verify_replay_evidence_readiness(require_finalized=True)` требует durable completeness, generation receipt и immutable finalization marker. |
| CHILD-253 | Strict exact replay mode | `DONE / BOUNDED LOCAL` | `require_finalized_replay=True` блокирует `replayed` до explicit promotion; после promotion fresh executor проходит replay. |
| CHILD-254 | Partial marker readiness denial | `DONE / BOUNDED LOCAL` | Interrupted permission phase fail-closed при startup readiness как `recovery_replay_finalization_not_immutable`. |
| CHILD-255 | Native/external readiness | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и external harness startup finalization не запускались. |

Focused strict-readiness result: `70/70` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-21 — Gate 3 partial-finalization repair checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-256 | Guarded operator repair | `DONE / BOUNDED LOCAL` | `repair_replay_evidence_finalization()` принимает только immutability-only partial failure, повторно проверяет trusted generation и архивирует marker. |
| CHILD-257 | Archive-before-repromotion | `DONE / BOUNDED LOCAL` | Partial marker перемещается в `_archive/`; active marker не удаляется молча и не перезаписывается напрямую. |
| CHILD-258 | Repair denial | `DONE / BOUNDED LOCAL` | Corrupt signature/schema/digest и уже finalized generation не repair-ятся автоматически. |
| CHILD-259 | Deterministic re-finalization | `DONE / BOUNDED LOCAL` | Re-finalized active marker byte-stable и strict fresh executor снова принимает generation. |
| CHILD-260 | Native/external repair | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и external operator repair не запускались. |

Focused repair result: `73/73` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-21 — Gate 3 signed repair provenance checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-261 | Signed repair receipt | `DONE / BOUNDED LOCAL` | `noesis.recovery-replay-finalization-repair.v1` связывает generation, archived marker SHA-256, active finalization SHA-256 и repair digest. |
| CHILD-262 | Archive path binding | `DONE / BOUNDED LOCAL` | Receipt принимает только independent regular file под bundle `_archive/` с expected finalization basename. |
| CHILD-263 | Cross-bundle substitution denial | `DONE / BOUNDED LOCAL` | Validly signed receipt со foreign archive path fail-closed как `recovery_replay_repair_receipt_archive_drift`. |
| CHILD-264 | Repair receipt tamper denial | `DONE / BOUNDED LOCAL` | Подмена finalization SHA-256 при valid signature fail-closed как finalization provenance drift. |
| CHILD-265 | Native/external repair provenance | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и external operator receipt lanes не запускались. |

Focused repair-provenance result: `75/75` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-21 — Gate 3 monotonic repair-chain checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-266 | Append-only repair chain | `DONE / BOUNDED LOCAL` | Signed JSONL chain с canonical path и strict sidecar discovery. |
| CHILD-267 | Monotonic repair IDs | `DONE / BOUNDED LOCAL` | `repair_id` начинается с 1, увеличивается без пропусков и связывается с previous repair digest. |
| CHILD-268 | Repair chain rotation | `DONE / BOUNDED LOCAL` | Prior active repair receipt архивируется перед следующим repair; history сохраняется. |
| CHILD-269 | Reorder/fork denial | `DONE / BOUNDED LOCAL` | Reordered records и digest fork fail-closed до finalization acceptance. |
| CHILD-270 | Native/external repair chain | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и external operator repair-chain lanes не запускались. |

Focused repair-chain result: `76/76` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-21 — Gate 3 repair-chain crash-consistency checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-271 | Durable chain append | `DONE / BOUNDED LOCAL` | Complete signed JSONL record flush-ится и `fsync()`-ится до read-only protection. |
| CHILD-272 | Partial terminal record | `DONE / BOUNDED LOCAL` | Truncated append fail-closed как `recovery_repair_chain_partial_record`. |
| CHILD-273 | File identity | `DONE / BOUNDED LOCAL` | Symlink/hardlink repair chain fail-closed как `recovery_repair_chain_file_identity`. |
| CHILD-274 | Strict startup denial | `DONE / BOUNDED LOCAL` | Active repair receipt не принимается при malformed, orphan или physically aliased chain. |
| CHILD-275 | Native/external crash recovery | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и external crash-consistency lanes не запускались. |

Focused crash-consistency result: `78/78` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-21 — Gate 3 repair-chain readiness snapshot checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-276 | Readiness audit | `DONE / BOUNDED LOCAL` | `audit_replay_chain_readiness()` публикует `noesis.recovery-repair-chain-readiness.v1`. |
| CHILD-277 | Observable states | `DONE / BOUNDED LOCAL` | Различаются `missing`, `partial`, `reordered`, `corrupt`, `immutable` и `passed`. |
| CHILD-278 | Diagnostic/acceptance separation | `DONE / BOUNDED LOCAL` | Non-throwing audit не заменяет fail-closed `verify_replay_evidence_readiness()`. |
| CHILD-279 | Native/external readiness snapshot | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и external telemetry lanes не запускались. |

Focused readiness result: `79/79` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-21 — Gate 3 signed repair-chain readiness checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-280 | Signed readiness receipt | `DONE / BOUNDED LOCAL` | Readiness receipt подписан и сохраняется read-only после repair. |
| CHILD-281 | Tip/finalization binding | `DONE / BOUNDED LOCAL` | `readiness_digest` связывает chain tip, ordered IDs и active finalization SHA-256. |
| CHILD-282 | Stale substitution denial | `DONE / BOUNDED LOCAL` | Validly re-signed snapshot с чужим tip fail-closed как readiness drift. |
| CHILD-283 | Native/external signed telemetry | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и external signed readiness lanes не запускались. |

Focused signed-readiness result: `80/80` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-21 — Gate 3 readiness cross-artifact binding checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-284 | Generation binding | `DONE / BOUNDED LOCAL` | Signed readiness связывает `generation_id` и `generation_digest` с current generation receipt. |
| CHILD-285 | Unified chain root | `DONE / BOUNDED LOCAL` | `chain_root_digest` и `event_chain_digest` обязаны совпадать с generation receipt root. |
| CHILD-286 | Cross-generation denial | `DONE / BOUNDED LOCAL` | Foreign generation/completeness/root substitution fail-closed как readiness drift. |
| CHILD-287 | Fresh-process acceptance | `DONE / BOUNDED LOCAL` | Новый executor принимает bound snapshot без regeneration evidence. |
| CHILD-288 | Native/external binding | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и external generation-binding lanes не запускались. |

Focused cross-binding result: `81/81` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-21 — Gate 3 finalized-evidence inventory checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-289 | Immutable inventory | `DONE / BOUNDED LOCAL` | Signed `noesis.recovery-replay-finalized-inventory.v1` inventory для finalized bundle. |
| CHILD-290 | Artifact coverage | `DONE / BOUNDED LOCAL` | Event chain, generation receipt, finalization, repair receipt, repair chain и readiness snapshot покрыты SHA-256 inventory. |
| CHILD-291 | Inventory digest | `DONE / BOUNDED LOCAL` | `inventory_digest` связывает generation, completeness, chain root и repair tip. |
| CHILD-292 | Orphan/substitution denial | `DONE / BOUNDED LOCAL` | Orphan sidecar и validly re-signed foreign inventory fail-closed. |
| CHILD-293 | Native/external inventory | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и external finalized-inventory lanes не запускались. |

Focused finalized-inventory result: `82/82` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-21 — Gate 3 inventory-verification receipt checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-294 | Verification receipt | `DONE / BOUNDED LOCAL` | Signed `noesis.recovery-replay-inventory-verification.v1` receipt создан для finalized inventory. |
| CHILD-295 | Acceptance binding | `DONE / BOUNDED LOCAL` | Receipt связывает inventory digest, generation digest, chain root, readiness и finalization status. |
| CHILD-296 | Stale/replay denial | `DONE / BOUNDED LOCAL` | Stale, modified или validly re-signed receipt fail-closed как verification drift. |
| CHILD-297 | Native/external verification | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и external verification-receipt lanes не запускались. |

Focused verification-receipt result: `83/83` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.


## 2026-08-21 — Gate 3 monotonic verification-run checkpoint

| ID | Область | Статус | Доказательство |
|---|---|---|---|
| CHILD-298 | Verification-run chain | `DONE / BOUNDED LOCAL` | Signed append-only `noesis.recovery-replay-inventory-verification-run.v1` JSONL chain. |
| CHILD-299 | Monotonic provenance | `DONE / BOUNDED LOCAL` | Positive run IDs, previous digest и event/run digests проверяются строго. |
| CHILD-300 | Replay/reorder denial | `DONE / BOUNDED LOCAL` | Reordered records и foreign inventory substitution fail-closed. |
| CHILD-301 | Native/external run history | `NOT_RUN / ENVIRONMENT-GATED` | Native Windows/macOS и external verification-run lanes не запускались. |

Focused verification-run result: `84/84` execution-recovery tests passed with Python 3.14.7, tracemalloc и `-W error::ResourceWarning`.
