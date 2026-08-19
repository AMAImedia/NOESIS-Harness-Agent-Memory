# Post-Transfer Audit

## Purpose

`scripts/post_transfer_audit.py` is the single post-transfer command for a copied NOESIS evidence directory. It performs three metadata-only stages in order:

| Stage | Check |
|---|---|
| Composition | Expected required files and optional report name/path. |
| Artifact chain | Inventory, aggregate, signed verification result, chain summary, cross-digest binding, and optional report bundle. |
| Reproducibility | Runtime/contract receipt and component digest binding. |

The command never reruns the pipeline, executes providers, launches child processes, makes network requests, or interprets artifact payloads.

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

A valid audit emits one JSON object with `status=passed` and exits `0`. The first failed stage is reported as `failed_stage` and exits `2`; composition failures prevent deeper checks from running. `automatic_execution=false` and `external_execution_claim=false` are invariant output fields.

This is a portable integrity and provenance audit. It does not establish native Windows/macOS execution, external lane execution, performance, or superiority claims.
