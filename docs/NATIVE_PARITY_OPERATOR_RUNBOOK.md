# Native Windows/macOS Parity Operator Runbook

This runbook is the operator-controlled preparation contract for Gate 6. It does not manufacture native evidence on Linux.

| Target | Command | Required host | Current Linux status |
|---|---|---|---|
| Windows | `pwsh -NoProfile -File scripts/run_native_parity.ps1` | Windows with Python 3.14.x | `not_run` |
| macOS | `zsh scripts/run_native_parity_macos.sh` | macOS with Python 3.14.x | `not_run` |

The bundle runs the existing Python 3.14 test suite, records an environment manifest, writes parity results, and requires network-off and credential-free execution. A target lane may report `passed` only after the matching host executes the bundle and produces the required artifacts: `environment.json`, `parity-results.json`, `sha256sums.txt`, and `sbom.json`.

A Linux dry-run or static inspection remains `not_run`; it is never converted into native success. The current machine-readable contract is [`CROSS_PLATFORM_RELEASE_GATE_MATRIX.json`](CROSS_PLATFORM_RELEASE_GATE_MATRIX.json), and the preparation API is `noesis_harness.native_parity`.
