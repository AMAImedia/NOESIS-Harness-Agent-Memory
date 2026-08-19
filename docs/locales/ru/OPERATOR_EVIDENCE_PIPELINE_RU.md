# Operator Evidence Pipeline

## Назначение

`scripts/run_operator_evidence_pipeline.py` — bounded operator entry point для external evidence ingestion. Он читает pinned manifest и переданные JSON evidence, создаёт readiness matrix и signed aggregate, а также может добавить verified aggregate в optional signed report bundle. Он никогда не запускает Hermes, OpenCode, DeepSeek Harness, providers, network requests или child runtimes.

## Артефакты и статусы

| Артефакт | Значение |
|---|---|
| `external-evidence-readiness.json` | Lane-level readiness matrix по `noesis.external-evidence-readiness.v1`. |
| `signed-external-evidence-aggregate.json` | HMAC-signed deterministic aggregate по `noesis.signed-external-evidence-aggregate.v1`. |
| Optional report ZIP | Signed report bundle с aggregate внутри `external_comparative.signed_evidence_aggregate`. |

Pipeline сохраняет aggregate status без преобразований. `passed` требует, чтобы все три lanes прошли существующий readiness contract. `not_run`, `blocked` и `unsupported` остаются явными и никогда не превращаются в success или score. Non-passed pipeline возвращает exit code `2`; malformed input или отсутствие required snapshot для `--report-output` также возвращают `2` и bounded JSON summary со `status=blocked`.

## Команда

```sh
python scripts/run_operator_evidence_pipeline.py \
  --manifest benchmarks/external_ab_manifest_v1.json \
  --evidence reports/hermes.json reports/opencode.json reports/deepseek-harness.json \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --output-dir reports/evidence-pipeline \
  --snapshot reports/operator-snapshot.json \
  --report-output reports/operator-report.zip
```

Команду безопасно запускать, когда external lanes недоступны. Missing или unpinned lanes остаются machine-readable `not_run` или `blocked`, а optional report bundle создаётся только при явно переданном snapshot. Поля `automatic_execution=false` и `external_execution_claim=false` являются invariant output fields.
