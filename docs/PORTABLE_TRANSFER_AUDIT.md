# Portable Transfer Audit

## Purpose

`scripts/transfer_audit.py` checks the composition of a transferred evidence directory before cryptographic verification. It is name-and-presence metadata only and never executes or interprets artifact contents.

## Expected composition

A strict transfer contains exactly these required files:

| File | Role |
|---|---|
| `artifact-manifest.json` | Signed SHA-256 inventory. |
| `external-evidence-readiness.json` | Readiness matrix. |
| `signed-external-evidence-aggregate.json` | Signed lane aggregate. |
| `verification-result.json` | Signed offline verification result. |
| `chain-summary.json` | Signed digest binding for the complete chain. |
| `reproducibility-receipt.json` | Signed runtime/contract fingerprint with timestamp excluded from the digest. |

`operator-report.zip` is optional. Other files are rejected in strict mode so debug logs, temporary outputs, or unreviewed sidecars cannot silently enter a transferred evidence set.

The Linux/macOS and Windows wrappers run strict mode by default. Direct Python invocation without `--require-signed-result` remains a legacy compatibility path for older sets, but new transfer audits should use the wrappers or strict flag. A composition mismatch returns `blocked` and exit code `2` before deeper verification.

This audit confirms expected artifact composition and complements, but does not replace, SHA-256, HMAC, cross-artifact, and report-bundle verification. It is not native packaging evidence and does not prove external execution.

The reproducibility receipt records Python implementation/version, platform system/machine, contract versions, and a stable timestamp policy. `observed_at`, when present, is intentionally excluded from the signed canonical payload so repeated verification remains deterministic. Runtime metadata is descriptive provenance, not native-host or performance evidence.
