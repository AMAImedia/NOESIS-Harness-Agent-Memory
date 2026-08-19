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

Успешная verification возвращает exit code `0`. Отсутствующая key, malformed input, signature failure, archive drift, missing domains или digest mismatch возвращают `2` и JSON со `status=blocked`. Verified bundle остаётся только результатом проверки export integrity с `claim=false`; это не comparative score и не native execution receipt.
