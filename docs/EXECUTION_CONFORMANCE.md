# Execution Conformance Contract

## Purpose

`scripts/execution_conformance.py` projects existing evidence into three independent execution classes: local clean-room replay, native host execution, and pinned external lanes. It never executes a provider, starts a child runtime, accesses a network, or upgrades a readiness status.

| Execution class | `passed` requires | Default when evidence is absent |
|---|---|---|
| `local_replay` | Clean-room replay, post-transfer audit, and final release gate all pass. | `blocked` or `not_run` |
| `native_host` | Host-bound readiness evidence and an explicit native execution claim. | `not_run` |
| `external_lanes` | Signed lane matrix, comparative readiness, and an explicit external execution claim. | `not_run` |

The report uses the fixed vocabulary `passed`, `not_run`, `blocked`, and `unsupported`. A contradictory snapshot or matrix is `blocked`; it is never downgraded to `not_run` and never promoted to `passed`.

## Command

```sh
python scripts/execution_conformance.py \
  --snapshot reports/evidence-pipeline/release-readiness.json \
  --matrix reports/evidence-pipeline/external-evidence-readiness.json \
  --replay reports/evidence-replay/replay-result.json \
  --gate reports/evidence-pipeline/release-gate.json \
  --output reports/evidence-replay/execution-conformance.json
```

The report is deterministic and carries `conformance_digest`. `automatic_execution=false`, `worldwide_superiority=false`, and `claim_boundary=execution_conformance_summary_only` are mandatory. Local replay can be passed while native and external classes remain `not_run`; this is an honest partial evidence state, not a global success claim.

## Boundaries

A clean-room replay cannot synthesize native Windows/macOS execution or external Hermes/OpenCode/DeepSeek Harness execution. Those classes require their own signed, host-bound receipts and matching pinned environments. The conformance report makes that distinction machine-readable for operators and downstream release gates.
