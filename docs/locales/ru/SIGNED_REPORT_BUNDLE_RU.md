# Deterministic signed report bundle

## Назначение

Report bundle экспортирует три отдельные evidence domains в один воспроизводимый архив: `local_execution`, `native_parity` и `external_comparative`. Domains остаются раздельными внутри bundle и имеют независимые digests.

Bundle использует `noesis.signed-report-bundle.v1`. ZIP entries имеют детерминированный порядок, фиксированные timestamps, фиксированные permissions, canonical JSON и не зависят от compression output. `manifest.json` содержит digest каждой domain и общий bundle digest. `signature.json` подписывает manifest через HMAC-SHA256.

| Domain | Значение | Claim boundary |
|---|---|---|
| `local_execution` | Локальное Python/Linux execution evidence. | Не означает native или external execution. |
| `native_parity` | Windows/macOS artifact или host parity readiness. | Linux dry-run остаётся `not_run`. |
| `external_comparative` | Readiness pinned Hermes/OpenCode/DeepSeek evidence. | Local export не создаёт competitor scores. |

Verification fail-closed для повреждённого ZIP, неожиданного набора файлов, manifest drift, signature tamper или domain digest mismatch. Успешная verification означает только целостность и воспроизводимость export; ничего не запускается, возвращается `claim=false` и `export_verification_only`.

Signing keys передаются operator и не записываются в archive. Export можно прикреплять к durable audit, но сам по себе он не является approval, execution receipt или comparative result.
