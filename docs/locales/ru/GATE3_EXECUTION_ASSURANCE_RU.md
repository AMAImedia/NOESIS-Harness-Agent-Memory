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

English primary contract: [`GATE3_EXECUTION_ASSURANCE.md`](../../GATE3_EXECUTION_ASSURANCE.md).
