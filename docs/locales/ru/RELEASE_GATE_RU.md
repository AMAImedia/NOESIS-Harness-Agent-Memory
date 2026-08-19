# Unified Release Gate

## Назначение

`scripts/release_gate.py` объединяет две существующие offline checks без rerun pipeline:

| Stage | Input | Значение |
|---|---|---|
| `post_transfer_audit` | Evidence directory и signing key | Composition, full chain и reproducibility integrity. |
| `release_readiness_snapshot` | `release-readiness.json` | Snapshot digest и claim-boundary integrity. |

Вторая stage запускается только после успешной первой. Result сохраняет outputs обеих stages и указывает первую failed stage в `failed_stage`.

```sh
./scripts/release_gate.sh \
  --root reports/evidence-pipeline \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --snapshot reports/evidence-pipeline/release-readiness.json
```

Полностью passed gate возвращает один JSON object со `status=passed` и exit code `0`. Любая missing, blocked, unsupported, malformed или tampered stage возвращает `status=blocked` и exit code `2`. Gate не преобразует non-passed native или external states в success.

Gate является только integrity/readiness composition. Он не доказывает native Windows/macOS execution, external lane execution, performance или worldwide superiority.
