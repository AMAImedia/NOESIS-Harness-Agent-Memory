# Release Readiness Verifier

`scripts/verify_release_readiness.py` independently verifies a transferred `release-readiness.json` snapshot. It reads one JSON file, checks its deterministic digest and claim boundaries, and performs no pipeline rerun, provider call, child-process launch, network request, or artifact execution.

```sh
./scripts/verify_release_readiness.sh \
  --snapshot reports/evidence-pipeline/release-readiness.json
```

```powershell
.\scripts\verify_release_readiness.ps1 `
  --snapshot reports\evidence-pipeline\release-readiness.json
```

A valid snapshot returns one JSON object with `status=passed` and exit code `0`. Missing, malformed, tampered, or claim-inconsistent snapshots return `status=blocked` and exit code `2`. The verifier does not reinterpret `not_run`, `blocked`, or `unsupported` native/external states as passed.
