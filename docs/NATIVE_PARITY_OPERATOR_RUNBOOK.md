# Native Windows/macOS Parity Operator Runbook

This runbook is the operator-controlled preparation contract for Gate 6. It does not manufacture native evidence on Linux.

| Target | Command | Required host | Current Linux status |
|---|---|---|---|
| Windows | `pwsh -NoProfile -File scripts/run_native_parity.ps1` | Windows with Python 3.14.x | `not_run` |
| macOS | `zsh scripts/run_native_parity_macos.sh` | macOS with Python 3.14.x | `not_run` |

The bundle runs the existing Python 3.14 test suite, records an environment manifest, writes parity results, and requires network-off and credential-free execution. A target lane may report `passed` only after the matching host executes the bundle and produces the required artifacts: `environment.json`, `parity-results.json`, `sha256sums.txt`, and `sbom.json`.

After the bundle completes, the operator must run `python3.14 scripts/validate_native_parity.py --target windows --evidence-dir artifacts/native/windows` (or replace `windows` with `macos`). The CLI calls `validate_native_artifacts(target, evidence_dir)`. The validator rejects missing or malformed artifacts, failed environment guards, non-passed parity results, missing SBOM entries, empty SHA-256 manifests, and SHA-256 mismatches. A `passed` result from this validator means that the matching host produced internally consistent operator artifacts; it does not establish external benchmark superiority.

A Linux dry-run or static inspection remains `not_run`; it is never converted into native success. The current machine-readable contract is [`CROSS_PLATFORM_RELEASE_GATE_MATRIX.json`](CROSS_PLATFORM_RELEASE_GATE_MATRIX.json), and the preparation API is `noesis_harness.native_parity`.

## Windows recovery write-path note

The recovery JSON writer now preserves atomic replacement while handling a read-only regular destination on Windows: it temporarily restores write permission only when required, performs `os.replace`, and restores the prior mode even on failure cleanup. Symlink targets are rejected. The focused regressions `test_atomic_json_replace_preserves_read_only_mode` and `test_repair_chain_rotates_monotonically_and_rejects_reorder` passed on CPython 3.11 with `ResourceWarning=0`. Full native Python 3.14 parity and signed package validation remain host-gated and are not claimed here.

The complete `tests.test_execution_recovery` discovery remains a bounded diagnostic concern on this Windows lane; individual repair/finalization cases pass, and a timeout is reported as incomplete evidence rather than success.

The read-only release audit accepts `--remote --remote-branch windows-autoloop` for branch-specific parity. Omitting `--remote-branch` retains the historical `main` default; a mismatch is reported as audit failure rather than silently treating another branch as equivalent. Empty, option-like, or whitespace-containing branch names fail closed with a structured `remote_error`.
