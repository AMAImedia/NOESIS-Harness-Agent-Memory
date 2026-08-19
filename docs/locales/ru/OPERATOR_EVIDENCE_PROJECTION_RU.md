# Контракт operator evidence projection

## Назначение

HealthServer показывает signed aggregate evidence как ограниченную read-only projection. Она помогает operator различать local execution evidence, native parity и external comparative readiness; сама projection не может выполнять, импортировать, утверждать или усиливать claims.

Aggregate доступен как `evidence_aggregate` в operator snapshot и telemetry, а также в `/api/readiness`. Projection принудительно устанавливает `comparative_claim=false` и обозначает границу `read_only_evidence_status`, даже если upstream provider передал более сильные поля.

| Surface | Значение | Управляющая возможность |
|---|---|---|
| `evidence_aggregate` | Статус проверки локально агрегированных receipts. | Только read-only. |
| `migration_readiness` | Статус operator-owned storage migration. | На GET surfaces только read-only. |
| Native parity readiness | Статус matching-host artifacts/execution. | Linux simulation не становится passed. |
| External comparative readiness | Evidence exact pinned external lanes. | Local aggregate не может его заполнить. |

Отсутствие provider обозначается `not_run`, ошибка provider — `blocked`. Секреты, включая signing keys, не показываются. SSE и UI получают такую же bounded projection без mutation action.

> Status projection — это граница наблюдения. Она не является authorization boundary и не превращает local evidence в comparative claim.
