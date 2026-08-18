# Build Policy Honesty Gate

The bounded build-policy runner verifies packaging and signing policy without executing a native Windows or macOS build.

| Lane | Result | Boundary |
|---|---|---|
| Windows dry-run | `passed` | Command is inspected but not run because the host is Linux. |
| macOS dry-run | `passed` | Command is inspected but not run because the host is Linux. |
| Signing policy | `passed` | Authenticode and codesign requirements are present; no signature was produced or verified. |
| Python 3.14 dry-run | `passed` (`3.14.7`) | Local interpreter identity is verified. |

The report is [`PARALLEL_BUILD_POLICY_EVIDENCE.json`](PARALLEL_BUILD_POLICY_EVIDENCE.json). Its mandatory guard fields are `native_builds_executed=false`, `network_allowed=false`, `credentials_available=false`, `model_generated_code_executed=false`, and `run_permitted=false` for target dry-runs.

A dry-run pass validates policy and refusal behavior. It does not create a Windows `.exe`, macOS `.app`, Authenticode signature, codesign result, notarization result, or native execution evidence.
