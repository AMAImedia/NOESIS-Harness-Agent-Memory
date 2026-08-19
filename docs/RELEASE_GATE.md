# Unified Release Gate

## Purpose

`scripts/release_gate.py` composes two existing offline checks without rerunning the pipeline:

| Stage | Input | Meaning |
|---|---|---|
| `post_transfer_audit` | Evidence directory and signing key | Composition, full chain, and reproducibility integrity. |
| `release_readiness_snapshot` | `release-readiness.json` | Snapshot digest and claim-boundary integrity. |

The second stage runs only after the first passes. The result preserves both stage outputs and reports the first failed stage as `failed_stage`.

```sh
./scripts/release_gate.sh \
  --root reports/evidence-pipeline \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --snapshot reports/evidence-pipeline/release-readiness.json
```

A fully passing gate returns one JSON object with `status=passed` and exit code `0`. Any missing, blocked, unsupported, malformed, or tampered stage returns `status=blocked` and exit code `2`. The gate does not convert non-passed native or external states into success.

The gate is an integrity/readiness composition only. It does not prove native Windows/macOS execution, external lane execution, performance, or worldwide superiority.

An existing `release-gate.json` can be checked for consistency with `--gate-artifact`. When the file is present under the evidence root, post-transfer audit also verifies its digest automatically. A tampered or malformed optional artifact is reported as a separate `release_gate_artifact` stage and fails closed; absence remains allowed for older transfers.
