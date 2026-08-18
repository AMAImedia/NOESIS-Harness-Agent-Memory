# Аудит self-learning, agent loop, OS surface и синхронизации документации

**Дата аудита:** 2026-08-18  
**Репозиторий:** `AMAImedia/NOESIS-Harness-Agent-Memory`  
**Проверенный commit:** `3a5e8c81867d3a80122e8d9f32b884a744b3aaad`

## Вывод

NOESIS-Harness-Agent-Memory имеет проверенное local-first ядро agent OS и bounded foundation для work loop. Но это ещё не полностью автономный product-level self-learning loop уровня зрелой системы создания skills и не native Windows/macOS или external benchmark distribution.

Система сильнее prompt-only loop: sessions, tasks, leases, approvals, child-process control, provenance, recovery, SSE telemetry и fail-closed evidence представлены кодом и тестами. При этом текущий agent loop — это execution primitive: он получает lease, вызывает injected action, сохраняет optional memory item и возвращает результат. Полный lifecycle `observe → evaluate → propose → approve → promote → verify` ещё не реализован как единый продуктовый контур.

## Gap matrix

| Возможность | Статус | Граница |
|---|---|---|
| Agent action loop с lease ownership | `implemented / locally verified` | `agent_loop.py`, coordination и multi-agent tests |
| Durable sessions/tasks и recovery | `implemented / locally verified` | Session/task APIs, SQLite event state, recovery и chaos tests |
| Memory tiers, provenance, confidence, decay и conflicts | `implemented / locally verified` | Memory/evidence/context/consolidation modules и focused tests |
| Experience reuse со scope/provenance checks | `implemented / locally verified` | `experience_reuse.py` и tests |
| Multi-agent leases, signals, dependencies и cancellation | `implemented / locally verified` | `coordination.py`, governance и multi-agent tests |
| Skill import/store/version/rollback safety | `implemented / bounded` | Import/store/rollback есть; executable skill entrypoints намеренно disabled |
| Автономный self-learning loop | `partial / not product-complete` | Нет полного evaluator-driven promotion lifecycle и automatic verified activation |
| Human-approved learning promotion | `partial / contract-ready` | Approval/governance primitives есть; end-to-end proposal-to-promotion workflow остаётся следующим gate |
| OS/control plane: sessions, tasks, approvals, recovery | `implemented / locally verified` | Versioned command API и recovery evidence |
| OS/control plane: child runtime и sandbox | `implemented / Linux verified` | Bubblewrap verified; Windows/macOS native lanes `not_run` |
| OS/control plane: SSE/operator telemetry | `implemented / locally verified` | `/api/telemetry`, `/api/child-runtimes`, bounded SSE dashboard |
| Native Windows/macOS packaging | `source/static policy only` | Реальные `.exe`/`.app` требуют matching hosts и native Python 3.14 evidence |
| External Hermes/OpenCode/DeepSeek Harness execution | `not_run / blocked` | Нет exact revisions, executables и disposable approved environments |
| English primary code/docs policy | `passed` | Normative contracts на английском; primary code-facing scope без кириллицы |
| Russian supplemental localization | `passed` | Localizations находятся в `docs/locales/ru/` |
| Code/docs/GitHub synchronization | `passed at audit checkpoint` | Link, security, JSON evidence, release metadata и parity checks прошли |

## Что уже является OS

Проект уже является **local-first agent OS kernel/control plane**, но ещё не законченным cross-platform distribution. Проверенное ядро включает durable sessions/tasks, explicit approvals, recovery, multi-agent coordination, child-process primitives, Linux sandbox conformance, signed evidence ingestion, operator telemetry и portable/static packaging policy.

Пока нельзя называть проект завершённой native Windows/macOS OS distribution, полностью автономной self-improving platform или benchmark-proven superior system.

## Следующий self-learning gate

Следующий high-leverage gate — **Human-Governed Learning Promotion Pipeline**:

1. Сохранять experience record завершённой задачи с provenance, scope, policy context и outcome receipt.
2. Запускать deterministic evaluator на holdout task set с evaluator version и evidence digest.
3. Создавать review-only learning proposal; не изменять active skills/policy автоматически.
4. Требовать explicit approval и scoped promotion decision.
5. Устанавливать immutable skill/experience version transactionally с rollback.
6. Перед activation повторять holdout, leakage, regression и rollback tests.
7. Выпускать signed promotion receipt и показывать lifecycle в operator telemetry.

До реализации этого gate memory и experience reuse следует называть **provenance-aware reuse и governance primitives**, а не полноценным self-learning loop.

Нормативная English-версия: [`SELF_LEARNING_OS_SYNC_AUDIT.md`](../../SELF_LEARNING_OS_SYNC_AUDIT.md).
