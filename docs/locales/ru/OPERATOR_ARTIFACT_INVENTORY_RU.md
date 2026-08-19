# Operator Artifact Inventory

## Назначение

Unified evidence pipeline записывает `artifact-manifest.json` рядом с readiness и aggregate artifacts. Manifest имеет schema `noesis.operator-artifact-inventory.v1`, содержит sorted SHA-256 inventory, bounded provenance fields и подписывается operator key.

Inventory включает только files, находящиеся внутри pipeline output directory. Каждая entry содержит POSIX relative path, byte size и SHA-256 digest. Сам inventory file записывается после перечисленных artifacts и намеренно не включается в собственный file list, чтобы избежать recursive hashing.

## Verification

`verify_inventory()` fail-closed при schema drift, inventory digest mismatch, signature mismatch, duplicate paths, traversal paths, missing files, size drift, content drift или `automatic_execution=true`. Verification читает только bytes; inventory-listed file не выполняется и не импортируется.

| Field | Значение |
|---|---|
| `inventory_digest` | SHA-256 digest canonical unsigned inventory. |
| `signature` | HMAC-SHA256 canonical unsigned inventory. |
| `provenance` | Pipeline schema, readiness status, comparative readiness и required lanes. |
| `automatic_execution` | Всегда `false`; inventory является observational metadata. |

Optional report bundle должен находиться внутри pipeline output directory, если включается в inventory. Это containment rule не позволяет оператору незаметно подписать unrelated files за пределами bounded artifact root.

## Operator workflow

```sh
python scripts/run_operator_evidence_pipeline.py \
  --manifest benchmarks/external_ab_manifest_v1.json \
  --evidence reports/hermes.json reports/opencode.json reports/deepseek-harness.json \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --output-dir reports/evidence-pipeline \
  --snapshot reports/operator-snapshot.json \
  --report-output reports/evidence-pipeline/operator-report.zip
```

Pipeline summary возвращает manifest path и `artifact_manifest_digest`. Последующий audit может проверить каждый listed file против signed manifest до attachment artifact set к operator report.
