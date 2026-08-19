# Signed Report Bundle Operator Runbook

## Scope

This runbook creates and verifies the same deterministic report bundle on Linux, macOS, and Windows. The wrapper selects Python only; it does not build a native application, launch a provider, or claim native parity.

Set the signing key through an environment variable. Never place the key in JSON, command history, a repository file, or the bundle.

| Platform | Wrapper |
|---|---|
| Linux | `scripts/report_bundle.sh` |
| macOS | `scripts/report_bundle.sh` |
| Windows PowerShell | `scripts/report_bundle.ps1` |

## Input files

Prepare three JSON object files: `local.json`, `native.json`, and `external.json`. Their contents are status projections, not executable instructions. Keep `native.json` as `not_run` unless a matching native host produced verified evidence. Keep `external.json` as `not_run` until exact pinned lane receipts exist.

## Linux and macOS

```sh
export NOESIS_REPORT_SIGNING_KEY='use-an-operator-secret-at-least-16-bytes'
./scripts/report_bundle.sh create \
  --local reports/local.json \
  --native reports/native.json \
  --external reports/external.json \
  --output reports/noesis-report.zip
./scripts/report_bundle.sh verify --bundle reports/noesis-report.zip
```

## Windows PowerShell

```powershell
$env:NOESIS_REPORT_SIGNING_KEY = "use-an-operator-secret-at-least-16-bytes"
.\scripts\report_bundle.ps1 create `
  --local reports\local.json `
  --native reports\native.json `
  --external reports\external.json `
  --output reports\noesis-report.zip
.\scripts\report_bundle.ps1 verify --bundle reports\noesis-report.zip
```

A successful verification exits `0`. Missing keys, malformed input, signature failure, archive drift, missing domains, or digest mismatch exit `2` and return a JSON object with `status=blocked`. A verified bundle remains an export integrity result with `claim=false`; it is not a comparative score or native execution receipt.
