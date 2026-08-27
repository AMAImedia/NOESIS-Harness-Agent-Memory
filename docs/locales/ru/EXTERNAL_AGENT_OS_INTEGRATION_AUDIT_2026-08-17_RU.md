# Аудит интеграции с внешними agent-OS — 2026-08-17

## Решение

NOESIS **не следует** перестраивать путём прямого копирования Cloudflare OS, Hermes Agent или OpenCode. Их сильнейшие идеи должны быть переведены в явные NOESIS-контракты и optional adapters. Ядро memory/security должно оставаться Python 3.14-only и stdlib-first; внешние runtime не должны становиться скрытыми обязательными зависимостями.

## Сравнение источников

| Источник | Лицензия/наблюдаемый статус | Ценные идеи | Почему он не может быть ядром NOESIS |
|---|---|---|---|
| Cloudflare OS | Apache-2.0; early-access репозиторий | Agent chat UI, sandboxed gadgets, capability-based Gatekeepers, отложенный human approval с simulation, private workspace instances и accountable agents | Построен вокруг TypeScript, Workers, Durable Objects, Dynamic Workers, Facets, Cap'n Web и `workerd`; cloud/runtime-модель не является Python stdlib portable core [1] |
| Cloudflare Sandbox SDK | Apache-2.0; beta | Изолированные контейнеры, command execution, file operations, streaming, per-sandbox workspaces и service exposure | Требует Node.js, Docker/containers и Cloudflare deployment/runtime-предположений; полезен как optional remote sandbox adapter, но не как local-first baseline [2] |
| Hermes Agent | MIT | Interactive CLI/TUI, gateway surfaces, persistent curated memory, session search, skills, learning loop, scheduling и parallel delegates | Широкий runtime имеет Python/Node/native/tool-зависимости и исполняет tools/skills; NOESIS должен сохранить более строгие deny-by-default и provenance/rollback boundaries [3] |
| OpenCode | MIT | Terminal/desktop/IDE surfaces, plan vs build modes, undo/redo, model/provider configuration, subagents и coding workflow | OpenCode — отдельный продукт/runtime со своей реализацией и release surface; использовать его user-facing контракты как benchmark targets, а не как vendored implementation [4] |
| Claude Code | Проприетарный продукт; не источник интеграции | Полезный продуктовый benchmark: terminal/IDE/desktop/web, tools, skills/hooks, agents и sessions | Не копировать и не вендорить проприетарный код; использовать только публичное поведение как interoperability/benchmark reference [5] |

## Правила интеграции

Допустимо: реализовать совместимые концепции независимо; определить NOESIS-native command/session/skill schemas; писать optional provider и sandbox adapters; документировать вдохновения и сохранять license notices при фактическом переиспользовании кода; использовать внешние продукты как black-box benchmark targets.

Недопустимо: копировать исходные файлы без provenance review; импортировать Node/npm/Workers как скрытые core-зависимости; заявлять subprocess hardened sandbox; выдавать skills неограниченный filesystem/network access; считать simulated approval результаты реальными side effects.

## Конкретные трансляции в NOESIS

| Внешняя концепция | Целевая NOESIS-native реализация |
|---|---|
| Cloudflare Gatekeeper | `CapabilityGate` с typed tool request, scope, side-effect class, dry-run/simulation result, approval ticket, commit/reject decision и append-only audit |
| Cloudflare gadget | Per-agent workspace с manifest, owner, capability set, resource budget, snapshot lineage и destroy/recover lifecycle |
| Cloudflare delayed approval | Двухфазное tool action: сначала prepare/simulate, затем явный commit; simulation должна помечаться как simulated и никогда не попадать в factual memory как завершённый side effect |
| Hermes memory/session search | Существующий provenance-aware memory плюс versioned session store, FTS/search index и отдельный durable session transcript; без silent memory overwrite |
| Hermes skills | `.noesisskill` manifest плюс executable child runtime, immutable version, digest, capability allowlist, workspace mount policy, timeout, output limit и rollback |
| OpenCode plan/build/undo | Task/session API с `plan`, `approve`, `execute`, `review`, `commit`, `rollback`, `resume`; read-only plan mode и patch-based change review |
| OpenCode subagent | Multi-agent lease/claim model, расширенная isolated workspace, recipient scope, budget, parent task, evidence handoff и conflict-free merge |
| Desktop/web/TUI surfaces | Один versioned session API с независимыми Python stdlib Web UI, terminal client и optional Tauri shell; никакая surface не может обходить capability gates |

## Граница безопасности для child execution

Child runtime должен рассматриваться как capability broker, а не magic sandbox. Каждый invocation требует signed/hashed request envelope, agent/tenant/session identity, executable или skill identity, явный argv, environment allowlist, workspace root, read/write mounts, network policy, CPU/time/output budgets и approval state. Родитель получает структурированные stdout/stderr/result envelopes и никогда не доверяет free-form output как завершённому side effect.

Первая реализация должна поддерживать local restricted profile и явно сообщать ограничения. Hardened OS isolation, container isolation или remote Cloudflare Sandbox execution должны быть отдельными адаптерами со своей верификацией. Если hardened adapter недоступен, опасные tools остаются `unavailable`, а не молча fallback-ятся в unrestricted execution.

## Ссылки

[1]: https://github.com/cloudflare/cloudflare-os "Cloudflare OS repository"

[2]: https://github.com/cloudflare/sandbox-sdk "Cloudflare Sandbox SDK"

[3]: https://github.com/NousResearch/hermes-agent "Hermes Agent repository"

[4]: https://github.com/anomalyco/opencode "OpenCode repository"

[5]: https://code.claude.com/docs/en/overview "Claude Code overview"

## Детали верификации лицензий

Официальный файл Cloudflare OS `LICENSE` — Apache License 2.0. Условия редистрибуции включают: приложение лицензии, маркировку модифицированных файлов, сохранение copyright/patent/trademark/attribution notices и включение применимых `NOTICE` attribution. Apache-2.0 также включает patent grant с termination clause при patent litigation против работы.

Официальный файл Hermes Agent `LICENSE` — MIT. Разрешает use, copying, modification, merging, publication, distribution, sublicensing и sale при условии, что copyright и permission notice включены в копии или substantial portions; предоставляется без warranty.

Официальный файл OpenCode `LICENSE` — MIT с тем же требованием сохранения notice. Репозиторий Cloudflare Sandbox SDK указывает из top-level `LICENSE` на `packages/sandbox/LICENSE`; package-level license должна быть проверена и сохранена перед вендорингом любого кода. README репозитория идентифицирует SDK как Apache License 2.0, но package-level provenance по-прежнему определяет точные переиспользуемые файлы.

Эти разрешения не делают все проекты эквивалентными: Apache-2.0 и MIT имеют разные формулировки notice, patent и redistribution, и каждый репозиторий может содержать отдельно лицензированные зависимости, assets, examples или сгенерированные файлы. Финальный дистрибутив NOESIS должен содержать third-party attribution inventory и не должен использовать upstream trademarks для implied endorsement.

Проверенные источники:

- https://github.com/cloudflare/cloudflare-os/blob/main/LICENSE
- https://github.com/cloudflare/sandbox-sdk/blob/main/LICENSE
- https://github.com/NousResearch/hermes-agent/blob/main/LICENSE
- https://github.com/anomalyco/opencode/blob/dev/LICENSE

Package-level `packages/sandbox/LICENSE` также проверена напрямую и представляет Apache License 2.0. Следовательно, код Sandbox SDK переиспользуем на условиях Apache-2.0 с оговоркой о сохранении notices, проверкой dependency tree и отделением Cloudflare-специфичных runtime-предположений от NOESIS local execution.

Дополнительный проверенный источник: https://github.com/cloudflare/sandbox-sdk/blob/main/packages/sandbox/LICENSE
