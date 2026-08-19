# Offline Operator Artifact Verifier

## Назначение

`scripts/verify_operator_artifact_set.py` проверяет transferred pipeline artifact directory без выполнения содержимого artifacts. Он проверяет `artifact-manifest.json`, каждый inventory-listed file, readiness matrix, signed external aggregate и optional report bundle.

## Cross-artifact checks

Verifier выполняет проверки в таком порядке:

1. Проверяет signed artifact inventory и все listed file digests внутри supplied root.
2. Требует readiness matrix и signed aggregate с ожидаемыми schemas.
3. Проверяет aggregate signature и требует, чтобы его `matrix_digest` совпадал с readiness matrix digest.
4. Если передан `--report`, требует, чтобы report ZIP находился внутри artifact root, и проверяет его operator key.
5. Возвращает aggregate readiness status, сохраняя `comparative_ready=false` и `external_execution_claim=false`, если evidence не поддерживает comparative claim.

Любой schema, signature, digest, missing-file, traversal, report-path или cross-artifact mismatch получает статус `blocked` и exit code `2`. Verification читает только JSON и ZIP metadata; artifact content не импортируется, не запускается и не интерпретируется.

## Команда

```sh
python scripts/verify_operator_artifact_set.py \
  --root reports/evidence-pipeline \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --report reports/evidence-pipeline/operator-report.zip
```

Successful result содержит `status=passed`, `checks.inventory.status=passed`, `checks.aggregate.status=passed` и `checks.cross_artifact_binding.status=passed`. `not_run`, `blocked` и `unsupported` остаются явными, если signed aggregate содержит эти states. Verifier portable для Linux, macOS и Windows, поскольку использует только Python standard-library file и archive operations.
