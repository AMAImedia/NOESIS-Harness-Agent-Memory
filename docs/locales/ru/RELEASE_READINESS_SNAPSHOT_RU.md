# Release Readiness Snapshot

## Назначение

`noesis.release-readiness-snapshot.v1` — machine-readable summary уже созданных evidence. Он объединяет post-transfer audit status, validated Python test count, runtime version и native/external readiness states без выполнения новых операций.

Snapshot можно создать так:

```sh
python scripts/build_release_readiness.py \
  --audit-json reports/evidence-pipeline/post-transfer-audit.json \
  --output reports/evidence-pipeline/release-readiness.json \
  --test-count 619 \
  --python-version 3.14.7 \
  --native-status not_run \
  --external-status not_run
```

`overall_status` равен `passed` только если post-transfer audit прошёл и передан положительный validated test count. Native и external states остаются отдельно видимыми как `not_run`, `blocked`, `unsupported` или `passed`.

Snapshot явно записывает `native_execution=false`, `external_execution=false`, `worldwide_superiority=false` и `automatic_execution=false`, пока отдельный reviewed contract не подтвердит иное. Поэтому `passed` означает readiness local evidence package, а не external execution или мировой claim.

`snapshot_digest` deterministic. Runtime timestamps не включаются, поэтому одинаковые inputs создают одинаковые snapshots.
