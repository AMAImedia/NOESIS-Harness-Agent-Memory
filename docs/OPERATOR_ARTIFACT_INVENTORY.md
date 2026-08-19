# Operator Artifact Inventory

## Purpose

The unified evidence pipeline writes `artifact-manifest.json` beside its generated readiness and aggregate artifacts. The manifest is `noesis.operator-artifact-inventory.v1`, contains a sorted SHA-256 inventory, binds bounded provenance fields, and is signed with the operator key.

The inventory includes only files contained by the pipeline output directory. Each entry records a POSIX relative path, byte size, and SHA-256 digest. The inventory file itself is written after the listed artifacts and is intentionally excluded from its own file list to avoid recursive hashing.

## Verification

`verify_inventory()` fails closed for schema drift, inventory digest mismatch, signature mismatch, duplicate paths, traversal paths, missing files, size drift, content drift, or `automatic_execution=true`. Verification reads bytes only; it never executes or imports an inventory-listed file.

| Field | Meaning |
|---|---|
| `inventory_digest` | SHA-256 digest of the canonical unsigned inventory. |
| `signature` | HMAC-SHA256 over the canonical unsigned inventory. |
| `provenance` | Pipeline schema, readiness status, comparative readiness, and required lanes. |
| `automatic_execution` | Always `false`; the inventory is observational metadata. |

The optional report bundle must be placed inside the pipeline output directory when it is included in the inventory. This containment rule prevents an operator from silently signing unrelated files outside the bounded artifact root.

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

The pipeline summary returns the manifest path and `artifact_manifest_digest`. A later audit can verify every listed file against the signed manifest before attaching the artifact set to an operator report.
