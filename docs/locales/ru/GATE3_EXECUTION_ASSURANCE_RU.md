# Gate 3 — Execution Assurance и replay boundary

**Статус:** локальные Python 3.14 evidence пройдены; native Windows/macOS и external lanes остаются `not_run`.

## Contract

У каждого governed child execution run есть один immutable `request_id` и canonical request fingerprint. Fingerprint включает argv, resolved workspace, executable allowlist, environment, timeout/output budgets, network flag, skill manifest, skill identity и granted capabilities. Recovery ledger сохраняет fingerprint до запуска процесса.

Повторный вызов с тем же `request_id` после terminal state не запускается снова и получает `execution_replay_denied`. Повторный вызов с тем же ID, но другим fingerprint получает `execution_request_identity_conflict`. Interrupted `running` record остаётся видимым recovery и не считается новым запуском автоматически. Перевести его в `recovered` можно только через authenticated scoped `recover` action с injected handler, подтверждающим переход. Это явное действие не заявляет rollback и не запускает child повторно.

Signed execution receipt сохраняется до перевода recovery record в terminal state. Успешный child run получает recovery status `completed`; timeout, denial и failure получают соответствующие bounded terminal states. Recovery ledger никогда не заявляет rollback без отдельного recovery executor, который реально выполнил и подтвердил mutation.

## Security invariants

| Invariant | Требуемый результат |
|---|---|
| Повтор того же request | Denied с `execution_replay_denied` |
| Тот же ID с изменённой командой или policy inputs | Denied с `execution_request_identity_conflict` |
| Manifest execution без hardened backend | Denied; direct fallback запрещён |
| Network request без verified isolation | Fail-closed denied |
| Credential-like child output | Redacted и blocked |
| Receipt tampering или conflict | Rejected |
| Interrupted run | Explicit recovery-required state; только authenticated `recover` action может отметить его recovered |
| Recovery без explicit action | Остаётся `running`/recovery-required; automatic rollback и rerun запрещены |
| Automatic skill activation | Disabled; вынесена в отдельный runtime contract |

## Evidence boundary

Machine-readable artifact: [`GATE3_EXECUTION_ASSURANCE_EVIDENCE.json`](../../GATE3_EXECUTION_ASSURANCE_EVIDENCE.json). Он содержит только локальные deterministic evidence. Linux/Bubblewrap availability не доказывает Windows/macOS parity, а simulated или подготовленные Hermes/OpenCode/DeepSeek lanes не считаются external execution evidence.

Implementation отделена от memory и control plane. Parent process не импортирует и не выполняет model-generated skill code; executable skill activation требует отдельного reviewed runtime contract.

Для delegated multi-agent work products `execute_and_submit()` добавляет вторую границу: request workspace должен точно совпадать с claimed agent workspace; execution result должен быть `completed`; signed receipt должен находиться в runtime-owned receipt store и иметь outcome `committed`; только после этого head snapshot можно передать на independent review. Failed execution, отсутствующий receipt store, непроверенный receipt, cross-agent path или отсутствующий runtime отклоняются до изменения work-product state.

`TaskExecutionBridge.execute_runtime()` применяет ту же границу к approved parallel lanes. До старта lane он проверяет session и `waiting_approval`, сохраняет action-store lease/claim lifecycle, передаёт cancellation/deadline/retry в `SafeParallelExecutor` и отдаёт в `AgentLaneResult.output` только bounded execution metadata. Lane events не содержат workspace paths, stdout, receipt-store objects или child output. Runtime mismatch становится failed lane и не переводит task в review.

Task session store добавляет redacted `task_execution_evidence` event, связанный с task и receipt identity. `resume(session_id)` после повторного открытия event log строит последнюю bounded metadata projection: request, receipt и outcome. Повтор той же evidence idempotent; конфликтующий receipt для того же request ID отклоняется. Task в состоянии `review` нельзя запустить через bridge снова, потому что требуется новая `waiting_approval` transition.

English primary contract: [`GATE3_EXECUTION_ASSURANCE.md`](../../GATE3_EXECUTION_ASSURANCE.md).
