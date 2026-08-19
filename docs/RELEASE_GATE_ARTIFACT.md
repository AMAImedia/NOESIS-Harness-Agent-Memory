# Release-Gate Artifact

The optional `release-gate.json` artifact uses schema `noesis.release-gate-artifact.v1`. It stores the separate post-transfer and release-readiness stage outputs, a deterministic `artifact_digest`, and fixed claim boundaries.

Generate it with the release gate:

```sh
./scripts/release_gate.sh \
  --root reports/evidence-pipeline \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --snapshot reports/evidence-pipeline/release-readiness.json \
  --output reports/evidence-pipeline/release-gate.json
```

Verify it after transfer without rerunning the gate:

```sh
./scripts/verify_release_gate_artifact.sh \
  --artifact reports/evidence-pipeline/release-gate.json
```

A valid artifact returns `passed` and exit `0`; missing, malformed, tampered, or claim-inconsistent artifacts return `blocked` and exit `2`. The artifact is optional in transfer composition, but if present it is accepted only under the exact `release-gate.json` filename. It summarizes integrity/readiness evidence only and does not prove native execution, external execution, performance, or worldwide superiority.
