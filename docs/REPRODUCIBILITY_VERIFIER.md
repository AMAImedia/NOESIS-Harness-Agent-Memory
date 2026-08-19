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

For clean-room replay of a generated bundle, use:

```sh
python scripts/replay_operator_evidence_pipeline.py \
  --expected-root reports/evidence-pipeline \
  --manifest benchmarks/external_ab_manifest_v1.json \
  --evidence reports/hermes.json reports/opencode.json reports/deepseek-harness.json \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --replay-root reports/evidence-replay \
  --readiness-test-count 638 \
  --readiness-python-version 3.14.7
```

The replay root must be empty before execution. The command regenerates the bounded bundle from the declared manifest and evidence inputs, compares SHA-256 bytes for every generated component, checks the receipt runtime fingerprint against the active interpreter and host, then runs strict post-transfer and final release-gate verification. A dirty replay root, changed input, runtime drift, missing generated artifact, digest mismatch, or environment/status inconsistency fails closed. A clean-room replay cannot promote `native_host_status=passed` or `external_lanes_status=passed`; those statuses require their own host-bound receipts and are not synthesized by local replay.

The receipt's runtime fingerprint and contract versions are descriptive provenance. The signed payload excludes `observed_at` according to the declared timestamp policy, so adding an observation time does not change the receipt digest or signature. This verifier proves reproducibility metadata and component binding only; it is not native-host, performance, external-execution, or superiority evidence.
