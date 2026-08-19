# Unified Release Gate

## Назначение

`scripts/release_gate.py` объединяет две существующие offline checks без rerun pipeline:

| Stage | Input | Значение |
|---|---|---|
| `post_transfer_audit` | Evidence directory и signing key | Composition, full chain и reproducibility integrity. |
| `release_readiness_snapshot` | `release-readiness.json` | Snapshot digest и claim-boundary integrity. |
| `release_gate_artifact` | `release-gate.json` или `--gate-artifact` | Canonical gate digest и независимая stage-status consistency. |

Вторая stage запускается только после успешной первой. Result сохраняет outputs обеих stages и указывает первую failed stage в `failed_stage`.

```sh
./scripts/release_gate.sh \
  --root reports/evidence-pipeline \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --snapshot reports/evidence-pipeline/release-readiness.json
```

Полностью passed gate возвращает один JSON object со `status=passed` и exit code `0`. Любая missing, blocked, unsupported, malformed или tampered stage возвращает `status=blocked` и exit code `2`. Gate не преобразует non-passed native или external states в success.

Gate является только integrity/readiness composition. Он не доказывает native Windows/macOS execution, external lane execution, performance или worldwide superiority.

Существующий `release-gate.json` автоматически проверяется, если находится внутри evidence root; `--gate-artifact` позволяет передать явный путь. Gate проверяет canonical digest и независимо требует, чтобы artifact status, stages `post_transfer_audit` и `release_readiness_snapshot` совпадали с текущими результатами. Tampered, malformed, stale или status-inconsistent artifact возвращается отдельной `release_gate_artifact` stage и блокируется fail-closed. Отсутствие остаётся допустимым для старых transfers, которые не заявляют generated readiness bundle.
