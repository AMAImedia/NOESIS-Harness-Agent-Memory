# Operator runbook для signed report bundle

## Область

Runbook создаёт и проверяет один и тот же deterministic report bundle на Linux, macOS и Windows. Wrapper выбирает только Python; он не собирает native application, не запускает provider и не создаёт native parity claim.

Signing key задаётся через environment variable. Нельзя помещать key в JSON, command history, repository file или bundle.

| Platform | Wrapper |
|---|---|
| Linux | `scripts/report_bundle.sh` |
| macOS | `scripts/report_bundle.sh` |
| Windows PowerShell | `scripts/report_bundle.ps1` |

## Input files

Подготовьте три JSON object files: `local.json`, `native.json` и `external.json`. Это status projections, а не executable instructions. Оставляйте `native.json` как `not_run`, пока matching native host не создаст verified evidence. Оставляйте `external.json` как `not_run`, пока не получены exact pinned lane receipts.

## Linux и macOS

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

## Offline export из operator snapshot

Если bounded operator snapshot уже сохранён, можно экспортировать все три domains без ручной подготовки отдельных файлов. Без `--receipt-audit` создаётся backward-compatible v1 bundle. С verified lifecycle receipt audit JSON создаётся v2 bundle с отдельным audit-only domain `lifecycle_receipt_audit`:

```sh
export NOESIS_REPORT_SIGNING_KEY='use-an-operator-secret-at-least-16-bytes'
./scripts/export_operator_report.sh \
  --snapshot reports/operator-snapshot.json \
  --output reports/noesis-report.zip
./scripts/export_operator_report.sh \
  --snapshot reports/operator-snapshot.json \
  --receipt-audit reports/lifecycle-receipt-audit.json \
  --output reports/noesis-report-v2.zip
```

Команда использует только существующие snapshot projections. Отсутствующие local, native или external domains становятся `not_run`; provider и external lane не вызываются. PowerShell equivalent: `./scripts/export_operator_report.ps1 --snapshot reports/operator-snapshot.json --output reports/noesis-report.zip`; для v2 добавьте `--receipt-audit reports/lifecycle-receipt-audit.json`. Receipt audit file должен содержать `record_id`, `bundle_digest`, `audit_digest` и verified `receipts` array. Invalid или tampered input возвращает `2`, bundle не создаётся.

Успешная verification возвращает exit code `0`. Отсутствующая key, malformed input, signature failure, archive drift, missing domains или digest mismatch возвращают `2` и JSON со `status=blocked`. Verified bundle остаётся только результатом проверки export integrity с `claim=false`; это не comparative score и не native execution receipt.

## Authenticated operator action

`POST /api/report-export` принимает signed `noesis.report-export-action.v1` JSON object. Action создаётся тем же operator signing key, который настроен на server. Optional `receipt_audit_path` должен указывать на существующий absolute `.json` path и входит в signed action. Executor проверяет полный receipt audit до записи bundle. Без поля создаётся v1, с полем — v2. Action single-use; snapshot drift, path escape, malformed или stale receipts, signature mismatch и replay блокируются fail-closed. Endpoint не запускает providers, child runtimes или external lanes.

Пример формы action:

```json
{
  "schema_version": "noesis.report-export-action.v1",
  "action_id": "export-2026-08-19-001",
  "operator_id": "operator-1",
  "session_id": "session-1",
  "output_name": "report-v2.zip",
  "snapshot_digest": "<sha256-of-bounded-snapshot>",
  "receipt_audit_path": "/absolute/path/lifecycle-receipt-audit.json",
  "signature": "<hmac-sha256>"
}
```
