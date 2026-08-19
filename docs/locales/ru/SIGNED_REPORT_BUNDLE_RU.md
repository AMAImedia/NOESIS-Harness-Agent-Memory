# Deterministic signed report bundle

Report bundle без lifecycle receipt audit использует `noesis.signed-report-bundle.v1` и исходные три domains. Bundle с `lifecycle_receipt_audit` использует `noesis.signed-report-bundle.v2` и добавляет четвёртый audit-only domain. Verification v1 остаётся поддержанной.

Report bundle экспортирует отдельные evidence domains в один воспроизводимый архив:

| Domain | Значение | Claim boundary |
|---|---|---|
| `local_execution` | Локальное Python/Linux execution evidence. | Не означает native или external execution. |
| `native_parity` | Windows/macOS artifact или host parity readiness. | Linux dry-run остаётся `not_run`. |
| `external_comparative` | Readiness pinned Hermes/OpenCode/DeepSeek evidence. | Local export не создаёт competitor scores. |
| `lifecycle_receipt_audit` | Verified operator ingestion receipts. | Только audit; не закрывает execution, native, external или comparative lanes. |

ZIP entries, manifest digests и HMAC signature остаются deterministic. Receipt domain нормализуется перед signing: `claim=false`, `execution_claim=false`, `comparative_claim=false`, а все execution/native/external lane flags устанавливаются в `false`. Successful verification означает только целостность export и не запускает ничего.

## Authenticated operator export

`POST /api/report-export` принимает signed `noesis.report-export-action.v1` JSON object. Optional `receipt_audit_path` входит в signed action payload и должен указывать на существующий absolute `.json` file. Executor проверяет полный receipt audit тем же operator key до создания bundle. Без поля создаётся v1; с verified audit создаётся v2 с normalized audit-only domain `lifecycle_receipt_audit`. Action single-use. Replay, path failure, snapshot drift, malformed или stale receipt, signature mismatch и domain verification failure блокируются fail-closed и не создают completed export receipt.
