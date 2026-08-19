# Portable Transfer Audit

## Назначение

`scripts/transfer_audit.py` проверяет composition transferred evidence directory до cryptographic verification. Это только name-and-presence metadata; artifact contents не запускаются и не интерпретируются.

## Expected composition

Strict transfer содержит ровно следующие required files:

| File | Роль |
|---|---|
| `artifact-manifest.json` | Signed SHA-256 inventory. |
| `external-evidence-readiness.json` | Readiness matrix. |
| `signed-external-evidence-aggregate.json` | Signed lane aggregate. |
| `verification-result.json` | Signed offline verification result. |
| `chain-summary.json` | Signed digest binding полного chain. |

`operator-report.zip` является optional. Другие files в strict mode отклоняются, чтобы debug logs, temporary outputs или unreviewed sidecars не могли незаметно попасть в transferred evidence set.

Linux/macOS и Windows wrappers запускают strict mode по умолчанию. Direct Python invocation без `--require-signed-result` остаётся legacy compatibility path для старых sets, но для новых transfer следует использовать wrappers или strict flag. Composition mismatch возвращает `blocked` и exit code `2` до более глубоких проверок.

Audit подтверждает expected artifact composition и дополняет, но не заменяет SHA-256, HMAC, cross-artifact и report-bundle verification. Это не native packaging evidence и не доказательство external execution.
