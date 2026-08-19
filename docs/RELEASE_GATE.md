# Unified Release Gate

## Purpose

`scripts/release_gate.py` composes two existing offline checks without rerunning the pipeline:

| Stage | Input | Meaning |
|---|---|---|
| `post_transfer_audit` | Evidence directory and signing key | Composition, full chain, and reproducibility integrity. |
| `release_readiness_snapshot` | `release-readiness.json` | Snapshot digest and claim-boundary integrity. |
| `release_gate_artifact` | `release-gate.json` or `--gate-artifact` | Canonical gate digest and independent stage-status consistency. |

The second stage runs only after the first passes. The result preserves both stage outputs and reports the first failed stage as `failed_stage`.

```sh
./scripts/release_gate.sh \
  --root reports/evidence-pipeline \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --snapshot reports/evidence-pipeline/release-readiness.json
```

A fully passing gate returns one JSON object with `status=passed` and exit code `0`. Any missing, blocked, unsupported, malformed, or tampered stage returns `status=blocked` and exit code `2`. The gate does not convert non-passed native or external states into success.

The gate is an integrity/readiness composition only. It does not prove native Windows/macOS execution, external lane execution, performance, or worldwide superiority.

An existing `release-gate.json` is automatically checked when present under the evidence root; `--gate-artifact` can provide an explicit artifact path. The gate verifies its canonical digest and independently requires that the artifact status, `post_transfer_audit` stage, and `release_readiness_snapshot` stage agree with the current results. A tampered, malformed, stale, or status-inconsistent artifact is reported as a separate `release_gate_artifact` stage and fails closed. Absence remains allowed for older transfers that do not claim a generated readiness bundle.
