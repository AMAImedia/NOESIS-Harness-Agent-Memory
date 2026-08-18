# Native Evidence Honesty Gate

The local native-evidence runner executes four bounded lanes without building or signing a native Windows or macOS artifact.

| Lane | Local result | Claim boundary |
|---|---|---|
| Portable SHA/SBOM | `passed` | Verifies a local portable fixture, not a native artifact. |
| Static packaging manifests | `passed` | Verifies manifest policy only; no native build executed. |
| Python 3.14 identity | `passed` (`3.14.7`) | Confirms the local interpreter used by the lane, not target-host packaging. |
| Windows target matrix | `passed` as a verifier lane; evidence `not_run` | Linux host mismatch; no Windows `.exe` claim. |
| macOS target matrix | `passed` as a verifier lane; evidence `not_run` | Linux host mismatch; no macOS `.app` claim. |

The machine-readable report is [`PARALLEL_NATIVE_EVIDENCE.json`](PARALLEL_NATIVE_EVIDENCE.json). `native_builds_executed=false`, `network_allowed=false`, `credentials_available=false`, and `model_generated_code_executed=false` are mandatory guard fields.

A `passed` verifier lane means that the honesty rule was enforced. It does not mean that a target artifact was built, signed, notarized, or executed on Windows/macOS. Native claims require matching target hosts and Python 3.14 environments.
