# Native packaging runbook (Windows / macOS)

Stdlib-only, local-first packaging evidence. This runbook is the operator-facing
companion to the CI packaging job (`.github/workflows/ci.yml`); both must stay
marker-aligned — `scripts/check_ci_packaging_consistency.py` enforces it.

## Runtime

- Built and signed on **Python 3.14.7** (plan-authoritative runtime).
- `signtool` present on the Windows build host but used only with a CA-issued
  code-signing certificate; the current artifact is `--development-unsigned`.

## Commands (must match CI markers)

- `python scripts/verify_python314.py --json`
- `python scripts/build_portable_artifact.py`
- `python scripts/verify_portable_artifact.py`
- `python scripts/verify_native_artifact.py --target` for `target in windows macos`

## Honesty boundary

- `target_host_or_python_mismatch`: a Windows artifact is only ever claimed on a
  Windows host running the pinned Python; a macOS claim requires a macOS host.
- `native evidence` is recorded, never fabricated. Where a target host or signing
  certificate is unavailable the lane reports `not_run` / `blocked`.
- This runbook describes static packaging and verification only. It does NOT claim
  a released, notarized, or CA-signed native artifact.
