# Roadmap NOESIS от 25% до 100%

**Текущий статус:** примерно **25–35% от доказательной базы**, необходимой для честного заявления «лучший в мире». Локальное ядро развито значительно дальше, чем внешняя доказательная часть. Этот документ является планом работ, а не заявлением о превосходстве.

## Модель прогресса

| Рубеж | Цель доказательств | Условие |
|---|---:|---|
| 25% | Local governed kernel | Durable sessions, memory, approvals, multi-agent coordination, Linux isolation и recovery проверены локально |
| 40% | Integrated local OS | Control plane, telemetry, governed learning, child-runtime contracts и work-product loop интегрированы |
| 55% | Hardened local release candidate | Non-fixture memory/agent stress, chaos/recovery, leakage holdouts, integrity artifacts и portable packaging воспроизводимы |
| 70% | Native-ready release candidate | Matching Windows/macOS bundles дают parity evidence; Linux preparation не заменяет native execution |
| 85% | Comparative-ready system | Exact pinned Hermes/OpenCode/DeepSeek environments, одинаковые tasks, signed receipts и independent scoring доступны |
| 100% | Claim-ready evidence package | Repeated external A/B показывает значимое преимущество без регрессии safety, provenance, recovery и human control |

## Параллельные направления

**Track A — control plane и operator surface.** Завершить versioned task/session API, interactive streaming, SSE telemetry, approvals, diff/patch review, per-agent workspaces и session resume. Read-only endpoint `/api/operator/snapshot` объединяет health, model capabilities, readiness, telemetry и authenticated operator context с recursive secret redaction.

**Track B — governed self-learning.** Связать terminal outcomes с provenance, holdout, review-only proposal, explicit approval, immutable promotion, verification и rollback. Automatic activation без approval остаётся запрещённой.

**Track C — memory и long context.** Расширить реальные durable trajectories, multi-session reuse, decay, conflicts, compaction, attribution leakage, hard budgets и independent repeated evaluation.

**Track D — isolation и adversarial reliability.** Объединить Bubblewrap, Windows и macOS под единым conformance contract и расширить tests на filesystem/network/credentials, symlink, timeout, process tree, leakage, corrupted receipt и recovery.

**Track E — portable/native packaging.** Выпустить reproducible Python 3.14 layouts, SBOM, checksums и operator bundles; фактический Windows/macOS execution остаётся host-gated.

**Track F — external comparative lanes.** Получить immutable revisions и executables Hermes/OpenCode/DeepSeek Harness, использовать disposable workspaces, одинаковые budgets/tasks, signed evidence и independent scoring. Отсутствующие lanes остаются `not_run`/`blocked`.

## Integration gates

G-01 baseline integrity; G-02 local OS integration; G-03 learning governance; G-04 memory quality; G-05 isolation conformance; G-06 native parity; G-07 external A/B; G-08 final claim review.

Параллельные work units могут изменять только назначенные файлы и обязаны выпускать tests и machine-readable result. Объединение выполняется только после diff review, полного Python 3.14 validation, audits и clean Git tree. Local simulation никогда не повышается до external success.

**Честная интерпретация:** примерно **65–70% до production-ready leading agent OS**, но только **25–35% до доказанного worldwide-leading claim**. До 100% остаются native Windows/macOS execution, exact external pins, reproducible A/B и independent final review.

Нормативная English-версия: [`ROADMAP_25_TO_100.md`](../../ROADMAP_25_TO_100.md).
