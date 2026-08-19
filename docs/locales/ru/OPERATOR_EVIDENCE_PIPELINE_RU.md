# Operator Evidence Pipeline

## Назначение

`scripts/run_operator_evidence_pipeline.py` — bounded operator entry point для external evidence ingestion. Он читает pinned manifest и переданные JSON evidence, создаёт readiness matrix и signed aggregate, а также может добавить verified aggregate в optional signed report bundle. Он никогда не запускает Hermes, OpenCode, DeepSeek Harness, providers, network requests или child runtimes.

## Артефакты и статусы

| Артефакт | Значение |
|---|---|
| `external-evidence-readiness.json` | Lane-level readiness matrix по `noesis.external-evidence-readiness.v1`. |
| `signed-external-evidence-aggregate.json` | HMAC-signed deterministic aggregate по `noesis.signed-external-evidence-aggregate.v1`. |
| Optional report ZIP | Signed report bundle с aggregate внутри `external_comparative.signed_evidence_aggregate`. |
| Optional readiness bundle | `release-readiness.json`, `release-gate.json` и `signed-readiness-receipt.json`, создаваемые при передаче test count и Python version. |
| Execution conformance | `execution-conformance.json`, создаваемый вместе с readiness bundle; local replay остаётся `not_run`, если не передан verified result через `--conformance-replay`. |

Pipeline сохраняет aggregate status без преобразований. `passed` требует, чтобы все три lanes прошли существующий readiness contract. `not_run`, `blocked` и `unsupported` остаются явными и никогда не превращаются в success или score. Machine-readable summary содержит fixed `status_vocabulary` (`passed`, `not_run`, `blocked`, `unsupported`), per-lane `status_counts` и `exit_code`. Non-passed pipeline возвращает exit code `2`; malformed input или отсутствие required snapshot для `--report-output` также возвращают `2` и bounded JSON summary со `status=blocked`.

## Команда

```sh
python scripts/run_operator_evidence_pipeline.py \
  --manifest benchmarks/external_ab_manifest_v1.json \
  --evidence reports/hermes.json reports/opencode.json reports/deepseek-harness.json \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --output-dir reports/evidence-pipeline \
  --snapshot reports/operator-snapshot.json \
  --report-output reports/operator-report.zip \
  --readiness-test-count 636 \
  --readiness-python-version 3.14.7 \
  --native-status not_run \
  --external-status not_run \
  --conformance-replay reports/evidence-replay/replay-result.json
```

Команду безопасно запускать, когда external lanes недоступны. Missing или unpinned lanes остаются machine-readable `not_run` или `blocked`, а optional report bundle создаётся только при явно переданном snapshot. Поля `automatic_execution=false` и `external_execution_claim=false` являются invariant output fields.

При передаче `--readiness-test-count` и `--readiness-python-version` pipeline дополнительно создаёт `release-readiness.json`, `release-gate.json` и `signed-readiness-receipt.json`. Receipt связывает snapshot digest, gate artifact digest, readiness status, test count, Python version и HMAC-SHA256 signature. Native и external statuses остаются явными; `not_run` никогда не становится `passed`. После записи artifact inventory pipeline выполняет offline verification pass и создаёт `verification-result.json` со schema `noesis.signed-operator-artifact-verification.v1`. Result связывает inventory digest и check projections и подписывает их HMAC-SHA256. Generated `execution-conformance.json` является optional transfer artifact и исключён из `artifact-manifest.json`, чтобы избежать circular digest. Без `--conformance-replay` его local class явно имеет `not_run`; pipeline generation не считается replay success. Summary artifacts проверяются strict post-transfer audit. Это создаёт полный non-executing evidence chain без claim запуска external lane или native host.
