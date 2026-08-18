# NOESIS 1.0 — master-план развития

**Контрольная точка:** 2026-08-18, commit `3555f4d`
**Runtime policy:** только Python 3.14; детерминированное ядро — stdlib-only.
**Модель эксплуатации:** local-first, private-by-default, human-governed, fail-closed.

Это русская supplemental localization нормативного English master plan. Это план поставки, а не заявление о превосходстве. Формулировка «лучшие в мире» допустима только после сопоставимого pinned A/B, native-доказательств Windows/macOS и независимо воспроизводимых метрик.

## Что уже доказано локально

| Поверхность | Статус | Граница доказательства |
|---|---|---|
| Память, provenance, decay, conflicts, retrieval и bounded experience reuse | `passed / local` | Детерминированные и adversarial tests; универсальное превосходство памяти не заявляется |
| Durable sessions, task API, leases, cancellation, recovery и resume | `passed / local` | Python 3.14 regression и chaos/recovery tests |
| Multi-agent coordination и private scopes | `passed / bounded local` | Leakage, scope, duplicate-delivery и governance tests |
| Human-governed learning promotion | `passed / bounded local` | Receipt, evaluator, review proposal, approval, immutable version, rollback и signed evidence; executable activation отдельно ограничена |
| SQLite/WAL migration и signed mode audit | `passed / local` | Transactional state/audit, dual-read guard, rollback, HealthServer readiness и UI/SSE timeline |
| Child execution и Linux/Bubblewrap isolation | `passed / Linux local` | Conformance/fail-closed tests; native parity не выводится автоматически |
| Operator control plane и Cloudflare-style read-only telemetry UI | `passed / local` | Health, readiness, audit, child-runtime и bounded SSE contracts |
| Windows/macOS native sandbox и packaging | `not_run / нужен host` | Static manifests и refusal policy есть; native evidence отсутствует |
| Hermes/OpenCode/DeepSeek Harness external A/B | `not_run / нужна pinned environment` | Readiness и signed-ingestion contracts есть; внешний процесс не запускался |

## Оставшиеся gates

### Gate 1 — Bounded production learning lifecycle binding: текущая контрольная точка

Bounded production binding реализован: `ProductionLearningLifecycle` соединяет durable task store, terminal-event bridge, runtime-owned policy simulator и explicit operator action executor. Portable launcher подключает эту композицию к HealthServer только при явно заданном valid signing key. Путь остаётся явным:

`terminal task -> provenance receipt -> deterministic holdout -> review proposal -> independent approval -> immutable promotion -> verification -> signed receipt -> optional activation`.

Локальный facade gate проверен positive, negative, replay и activation-boundary tests. Завершение task не оценивает, не одобряет, не продвигает и не активирует skill скрыто. Для полного закрытия нужны durable promotion-state/evaluator deployment и operator UI workflow для явно зарегистрированных evaluators и proposals.

### Gate 2 — Durable promotion state and evaluator deployment (локальный gate закрыт)

Реализовано и проверено: receipts, evaluations, proposals, previous-active metadata и evaluator manifests сохраняются в SQLite/WAL; reopened pipeline восстанавливает bounded state; одинаковые retries idempotent; payload/content/manifest conflicts fail closed; `PromotionIntegration.snapshot()` показывает bounded counts и manifest digests через HealthServer/UI/SSE. Automatic activation остаётся отключённой. Полная Python 3.14 проверка: 430 тестов пройдено.

### Gate 3 — Governed executable skill/tool runtime (в работе)

Manifest/grant contract и Linux reference path реализованы: `ExecutionRequest` связывает optional `SkillManifest` с explicit granted capabilities; strict executable-skill mode требует available hardened backend; `BubblewrapBackend` предоставляет Linux namespace/network/filesystem boundary. HMAC-signed `ExecutionReceiptStore`, restart-safe `ExecutionRecoveryStore` и durable `PatchReviewStore` покрывают execution evidence, interrupted-run state и review status. Parent control plane не импортирует и не выполняет model-generated code. Windows/macOS остаются conformance targets до запуска на matching hosts.

Нужны тесты path escape, network egress, credential-like output, environment poisoning, symlink, timeout, process tree, corrupted receipt, interrupted write, receipt replay/tamper, patch-review conflict, authenticated rollback, stale-base и cross-agent workspace. Local Gate 3 subgates теперь покрыты: `ExecutionRecoveryExecutor` требует authenticated operator context, signed receipt/run identity, approved patch, fresh base и injected handler, подтверждающий фактическую mutation. Непроверенный backend получает `not_run`, `blocked` или `unavailable`, но не `passed`.

### Gate 4 — Реальный multi-agent work-product loop (в работе)

`MultiAgentWorkProductLoop` связывает exclusive task claims с typed `WorkProductEnvelope`, per-agent workspace snapshots, independent review, fresh-base merge authorization, explicit task commit markers и durable session resume/replay. Создающий агент не может approve собственный продукт, review не применяет файлы, а commit является отдельным authorized state transition. Остаются более широкий multi-agent execution, cross-agent leakage holdouts, crash recovery во время delegation и измеримые work-product benchmarks.

### Gate 5 — Качество памяти и длинного контекста

Провести воспроизводимые recall, attribution, conflict, temporal, compaction-retention, context-budget и experience-reuse benchmarks. Большой store или длинный prompt не считаются улучшением без роста correctness/attribution/recovery без leakage и превышения budget.

### Gate 6 — Native Windows/macOS evidence

Запустить одинаковый operator bundle и parity contract на matching Windows/macOS hosts с Python 3.14. Выпустить signed environment digests, backend conformance receipts, packaging manifests, SHA-256/SBOM и negative-path results. До этого статусы остаются `not_run`.

### Gate 7 — Pinned external A/B evidence

Получить exact immutable revisions и executable environments для Hermes, OpenCode и DeepSeek Harness. Использовать disposable workspaces, единый task protocol, одинаковый corpus/budget, independent scoring, signed receipts и explicit approval. Сравнить correctness, evidence quality, recovery, isolation, approval bypass, credential leakage, latency, reviewer time и ресурсы. Отсутствующая или mismatched environment остаётся `not_run`/`blocked`.

### Gate 8 — Release и public-claim review

После Gates 1–6 выполнить полный Python 3.14 suite, link/schema/security audits, reproducibility, clean-tree release audit, license/provenance review и localization audit. README должен явно разделять verified capabilities и unresolved boundaries.

## Правило синхронизации

Порядок работы: **(1) реализовать governed executable child runtime, (2) в одном focused change обновить код, tests, English docs, Russian docs и machine-readable evidence, (3) выполнить полную проверку, commit и remote verification, (4) связать end-to-end multi-agent work-product loop, (5) измерить memory quality gates и только потом запускать native/external lanes**. Gate не считается закрытым, если код, тесты, документация и evidence расходятся.

## Честный критерий завершения

«Лучшие в мире» — не текущий статус проекта, а проверяемая гипотеза. Она может быть рассмотрена только при pinned tasks/environments и meaningful advantage без ухудшения safety, provenance, recovery и human control. Сейчас корректное описание: **local-first, provenance-aware и human-governed agent OS kernel с проверенным Linux control plane и явными native/external readiness gates**.

English primary: [`PLAN_NOESIS_1.0_MASTER.md`](../../PLAN_NOESIS_1.0_MASTER.md).

## References

[1]: https://github.com/cloudflare/cloudflare-os "Cloudflare OS"
[2]: https://github.com/NousResearch/hermes-agent "Hermes Agent"
[3]: https://github.com/opencode-ai/opencode "OpenCode"
[4]: https://arxiv.org/abs/2608.13417 "arXiv:2608.13417"

Эти проекты и статья — design references и benchmark targets, а не доказательство запуска или превосходства NOESIS.
