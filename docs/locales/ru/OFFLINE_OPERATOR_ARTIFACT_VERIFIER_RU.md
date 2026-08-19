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

## Platform wrappers

Wrappers выбирают только Python и сохраняют одинаковый JSON stdout и exit-code contract:

| Platform | Wrapper | Success | Blocked/non-passed |
|---|---|---:|---:|
| Linux/macOS | `scripts/verify_operator_artifacts.sh` | `0` | `2` |
| Windows PowerShell | `scripts/verify_operator_artifacts.ps1` | `0` | `2` |
| Direct Python | `scripts/verify_operator_artifact_set.py` | `0` | `2` |

Wrappers не изменяют paths, не запускают содержимое artifacts и не добавляют platform-specific claims. Это wrapper parity evidence, а не native packaging evidence.

## Signed verification result

Используйте `--signed-output`, когда результат offline verification должен войти в последующую evidence chain:

```sh
./scripts/verify_operator_artifacts.sh \
  --root reports/evidence-pipeline \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --signed-output reports/evidence-pipeline/verification-result.json
```

Output schema — `noesis.signed-operator-artifact-verification.v1`. Он связывает verified inventory digest, check projections, verification status, deterministic result digest и HMAC-SHA256 signature. Signed result содержит `automatic_execution=false`, `external_execution_claim=false` и claim boundary `offline_artifact_verification_only`. Он доказывает только integrity transferred artifact set и не является evidence запуска external lane.
