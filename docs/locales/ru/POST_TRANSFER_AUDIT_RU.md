# Post-Transfer Audit

## Назначение

`scripts/post_transfer_audit.py` — единая post-transfer команда для скопированной NOESIS evidence directory. Она выполняет три metadata-only stages по порядку:

| Stage | Проверка |
|---|---|
| Composition | Expected required files, обязательный signed readiness receipt и optional report name/path. |
| Artifact chain | Inventory, aggregate, signed verification result, chain summary, cross-digest binding, signed readiness receipt, release-gate artifact и optional report bundle. |
| Reproducibility | Runtime/contract receipt и component digest binding. |

Команда не rerun-ит pipeline, не запускает providers, child processes, network requests и не интерпретирует artifact payloads.

## Commands

```sh
./scripts/post_transfer_audit.sh \
  --root reports/evidence-pipeline \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY"
```

```powershell
.\scripts\post_transfer_audit.ps1 `
  --root reports\evidence-pipeline `
  --key $env:NOESIS_EXTERNAL_EVIDENCE_KEY
```

Valid audit возвращает один JSON object со `status=passed` и exit `0`. Первая failed stage указывается в `failed_stage` и возвращает `2`; composition failures останавливают более глубокие проверки. В strict post-transfer path файл `signed-readiness-receipt.json` обязателен и должен связывать скопированные `release-readiness.json` и `release-gate.json` через digest, status, test count и HMAC-SHA256 signature. Отсутствующий, устаревший, изменённый или status-inconsistent receipt блокируется fail-closed. Поля `automatic_execution=false` и `external_execution_claim=false` являются invariant output fields.

Это portable integrity и provenance audit. Он не подтверждает native Windows/macOS execution, external lane execution, performance или superiority claims.
