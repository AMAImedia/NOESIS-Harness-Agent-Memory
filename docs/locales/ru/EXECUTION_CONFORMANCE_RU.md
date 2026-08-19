# Execution Conformance Contract

## Назначение

`scripts/execution_conformance.py` проецирует существующие evidence в три независимых execution classes: local clean-room replay, native host execution и pinned external lanes. Он никогда не запускает provider, child runtime или network operation и не повышает readiness status.

| Execution class | Что требуется для `passed` | Default при отсутствии evidence |
|---|---|---|
| `local_replay` | Clean-room replay, post-transfer audit и final release gate должны пройти. | `blocked` или `not_run` |
| `native_host` | Host-bound readiness evidence и явный native execution claim. | `not_run` |
| `external_lanes` | Signed lane matrix, comparative readiness и явный external execution claim. | `not_run` |

Report использует фиксированный vocabulary: `passed`, `not_run`, `blocked` и `unsupported`. Contradictory snapshot или matrix получают `blocked`; они не понижаются до `not_run` и никогда не повышаются до `passed`.

## Команда

```sh
python scripts/execution_conformance.py \
  --snapshot reports/evidence-pipeline/release-readiness.json \
  --matrix reports/evidence-pipeline/external-evidence-readiness.json \
  --replay reports/evidence-replay/replay-result.json \
  --gate reports/evidence-pipeline/release-gate.json \
  --output reports/evidence-replay/execution-conformance.json
```

Report является deterministic и содержит `conformance_digest`. Поля `automatic_execution=false`, `worldwide_superiority=false` и `claim_boundary=execution_conformance_summary_only` обязательны. Local replay может быть `passed`, пока native и external classes остаются `not_run`; это честное partial evidence state, а не global success claim.

## Границы

Clean-room replay не может синтезировать native Windows/macOS execution или external Hermes/OpenCode/DeepSeek Harness execution. Для этих классов нужны отдельные signed host-bound receipts и matching pinned environments. Conformance report делает это различие machine-readable для operators и downstream release gates.
