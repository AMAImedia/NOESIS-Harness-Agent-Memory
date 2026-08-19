# Release Readiness Snapshot

## Purpose

`noesis.release-readiness-snapshot.v1` is a machine-readable summary of already-produced evidence. It combines post-transfer audit status, validated Python test count, runtime version, and native/external readiness states without executing anything.

A local snapshot can be generated with:

```sh
python scripts/build_release_readiness.py \
  --audit-json reports/evidence-pipeline/post-transfer-audit.json \
  --output reports/evidence-pipeline/release-readiness.json \
  --test-count 619 \
  --python-version 3.14.7 \
  --native-status not_run \
  --external-status not_run
```

`overall_status` is `passed` only when the post-transfer audit passes and a positive validated test count is supplied. Native and external states remain independently visible as `not_run`, `blocked`, `unsupported`, or `passed`.

The snapshot explicitly records `native_execution=false`, `external_execution=false`, `worldwide_superiority=false`, and `automatic_execution=false` unless future verified evidence changes those states under a separately reviewed contract. A `passed` snapshot therefore means local evidence package readiness, not external execution or a worldwide-leading claim.

The `snapshot_digest` is deterministic. Runtime timestamps are not included, so identical inputs produce identical snapshots.
