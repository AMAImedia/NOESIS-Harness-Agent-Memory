# Signed External Evidence Aggregator

## Назначение

`scripts/aggregate_external_evidence.py` создаёт deterministic signed aggregate для receipt-backed readiness evidence ровно трёх required lanes: `hermes`, `opencode` и `deepseek_harness`. Это только ingestion и verification component. Он не устанавливает, не запускает, не вызывает и не управляет внешними executable.

## Contract

Aggregator сначала использует `noesis.external-evidence-readiness.v1`. Каждый accepted record должен иметь корректный HMAC envelope, exact pinned revision, matching environment digest при необходимости, deterministic receipt identity и общий protocol fingerprint. Duplicate system records, duplicate receipt IDs, stale receipts, signature failures, revision drift, environment drift, unsupported execution и protocol conflicts остаются явными lane/global statuses.

Output schema — `noesis.signed-external-evidence-aggregate.v1`. Evidence канонически сортируется по lane identity, revision, receipt ID и record digest до расчёта `evidence_digest` и signed aggregate. Aggregate содержит manifest digest, evidence digest, readiness matrix digest, все required lane projections, global checks и HMAC-SHA256 signature. Verification fail-closed при schema drift, digest mismatch, signature mismatch, lane identity mismatch или попытке установить `native_or_external_execution_claim=true`.

| Status | Значение |
|---|---|
| `passed` | Все три lanes прошли readiness verification. Это signed evidence aggregation, а не quality или superiority claim. |
| `not_run` | Отсутствует required revision или execution evidence без pinned contradictory record. |
| `blocked` | Не прошла pinned lane или глобальная identity/security проверка. |
| `unsupported` | Lane явно сообщает, что требуемый execution mode не поддерживается. |

## Claim boundary

`passed` aggregate доказывает только, что submitted evidence проверено против declared manifest и signing key. Он не доказывает, что текущий host запускал Hermes, OpenCode или DeepSeek Harness, и не ранжирует системы. Comparative scoring требует отдельного case-level evaluator, independent scoring rules, repeated runs и operator-approved evidence artifacts. Текущий external artifact репозитория остаётся `not_run`, пока matching pinned environments не создадут receipts.

## CLI

```sh
python scripts/aggregate_external_evidence.py \
  --manifest benchmarks/external_ab_manifest_v1.json \
  --evidence reports/hermes.json reports/opencode.json reports/deepseek-harness.json \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --output reports/signed-external-evidence-aggregate.json
```

Non-passed aggregate возвращает exit code `2`. Команда не создаёт executable configuration и никогда не превращает missing evidence в success.
