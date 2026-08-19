# Standalone Reproducibility Verifier

## Purpose

`scripts/verify_reproducibility_receipt.py` independently verifies `reproducibility-receipt.json` after an evidence directory has been transferred. It reads only the inventory, signed aggregate, chain summary, and reproducibility receipt. It does not rerun the pipeline, execute providers, launch child processes, make network requests, or inspect artifact payloads.

## Command contract

```sh
./scripts/verify_reproducibility.sh \
  --root reports/evidence-pipeline \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY"
```

```powershell
.\scripts\verify_reproducibility.ps1 `
  --root reports\evidence-pipeline `
  --key $env:NOESIS_EXTERNAL_EVIDENCE_KEY
```

A valid result returns one JSON object with `status=passed` and exit code `0`. Missing components, digest drift, wrong key, signature failure, malformed JSON, or claim-boundary violations return `status=blocked` and exit code `2`.

The receipt's runtime fingerprint and contract versions are descriptive provenance. The signed payload excludes `observed_at` according to the declared timestamp policy, so adding an observation time does not change the receipt digest or signature. This verifier proves reproducibility metadata and component binding only; it is not native-host, performance, external-execution, or superiority evidence.
