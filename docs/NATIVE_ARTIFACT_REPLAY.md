# Native Artifact Replay Contract

## Purpose

This contract verifies operator-produced Windows and macOS parity artifacts without executing an unverified native binary. It is an evidence boundary, not a substitute for matching-host execution.

## Report schema

The replay report uses `noesis.native-artifact-replay.v1` and contains the target, host platform, Python version, environment digest, validator status, and reason. It also records `execution_performed`, `native_execution_claim`, and `external_execution_claim` as explicit booleans.

| Status | Meaning | Claim allowed |
|---|---|---|
| `passed` | Matching host/Python identity and required artifacts validate successfully. | Artifact replay validation only; native execution is still not performed by the verifier. |
| `not_run` | The current host or Python version cannot verify the requested native target. | No native claim. |
| `blocked` | A matching host exists, but evidence is missing, malformed, stale, or fails an integrity/security guard. | No native claim. |

## Required invariants

The verifier requires `environment.json`, `parity-results.json`, `sha256sums.txt`, and `sbom.json`. The environment must deny network access and credentials. The parity result must explicitly be `passed` and carry an execution claim from the operator-produced receipt. The checksum manifest must match the environment and parity files, and the SBOM must enumerate the required evidence files.

The replay wrapper never invokes a provider, child process, native executable, network operation, or external lane. `artifact_replay_allowed=true` only indicates that the existing evidence passed static validation on a matching host. It does not create a native execution receipt or comparative external score.

## Operator commands

```text
python scripts/build_native_replay_report.py \
  --target windows \
  --evidence-dir ./native-evidence/windows \
  --platform win32 \
  --python-version 3.14.7 \
  --output ./reports/native-windows-replay.json
```

The command exits successfully only for `passed`. A `not_run` or `blocked` result is intentionally non-zero so automation cannot silently treat an unavailable or invalid native lane as verified.

## Boundary

Linux-produced static manifests and local simulations remain preparation evidence. Windows and macOS native parity move to `passed` only after the operator runs the supplied bundle on the corresponding matching host and imports a valid, signed receipt through the fail-closed ingestion lifecycle.
