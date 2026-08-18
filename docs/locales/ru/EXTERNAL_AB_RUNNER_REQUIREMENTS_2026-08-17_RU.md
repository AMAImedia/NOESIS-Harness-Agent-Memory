# External A/B runner requirements — 2026-08-17

## Confirmed interfaces

Hermes publishes a CLI with non-interactive single-query mode, explicit model/provider/toolset selection, session resume, isolated git worktree mode and multiple terminal backends. Its repository also contains `evals/`, `batch_runner.py` and `mini_swe_runner.py`, which are candidates for protocol inspection rather than assumptions of compatibility. Hermes is MIT-licensed [1].

OpenCode publishes a terminal, desktop and IDE experience. Its documented Plan mode disables changes, Build mode enables implementation, primary agents and subagents have different permissions, and configured permissions include `ask`, `allow` and `deny` for read/edit/bash/task/skill and other tools [2] [3]. OpenCode recommends WSL for Windows in its current installation documentation, so native Windows evidence must not be inferred from Linux/WSL execution [2].

## Required runner contract

A valid comparison requires exact pinned revisions for NOESIS, Hermes and OpenCode; a fixed model/provider or a separate model-agnostic protocol lane; identical task fixtures; identical context and step budgets; identical tool permissions; disposable workspaces; no user credentials; deterministic timeouts; and a common evaluator.

The evaluator must score task success, patch correctness, test pass rate, context retention, latency, token/cost budget, unauthorized egress, credential exposure, approval bypass, workspace escape, recovery after timeout/kill, and human review burden. A feature unavailable in one system must be recorded as `not_run` or measured in a separate capability lane, never silently treated as a zero failure.

## Execution gates

The first lane is model-agnostic and tests lifecycle/security contracts with deterministic fixtures. The second lane is coding-task A/B and requires each system to have the same model, repository snapshot and task prompt. The third lane is interactive UX and measures time-to-approval, time-to-recovery and operator error rate.

External execution cannot be claimed from documentation alone. Hermes/OpenCode must be installed or invoked through a user-provided/native runner, and the exact command, revision and environment must be recorded in the result manifest. Until those runners are available, the correct status is `not_run`.

## References

[1]: https://github.com/NousResearch/hermes-agent "NousResearch Hermes Agent repository and CLI documentation"
[2]: https://opencode.ai/docs/ "OpenCode official getting started documentation"
[3]: https://opencode.ai/docs/agents/ "OpenCode official agents and permissions documentation"


## Реализованный connector-neutral contract

` scripts/external_runner_contract.py` формирует `noesis.external-runner.v1`: команда хранится как argv-массив, а не shell string; фиксируются exact revision, SHA-256 task manifest, model/provider, disposable workspace, deny outside access и отсутствие credentials. Contract builder только создаёт spec и не запускает Hermes/OpenCode. Validator принимает только `passed`, `failed`, `unsupported` или `not_run` и fail-closed отклоняет shared workspace или shell-string command.

Simulated evaluator использует expanded 13-metric schema. Локальная contract lane может наблюдать только deterministic contract metrics; patch correctness, context retention, provider cost, egress, credential exposure, approval bypass, workspace escape, kill/timeout recovery и operator burden остаются `not_run`, пока не появится pinned external runner.


## Evidence ingestion и подпись

` scripts/ingest_runner_result.py` принимает только result, совпадающий с pinned runner spec по system, revision, task-manifest SHA-256, argv и disposable workspace. Metric status ограничен `passed`, `failed`, `unsupported`, `not_run`; credential-like content, shared workspace и identity mismatch отклоняются.

Принятый evidence record имеет schema `noesis.runner-evidence.v1` и HMAC-SHA256 integrity envelope. Ключ передаётся только во время запуска и не попадает в JSON. Это operator integrity/authenticity mechanism, а не замена публичной release-подписи; для внешней публикации дополнительно потребуются защищённое хранение ключа, provenance и platform signing.


## Unified signed-evidence evaluation

` scripts/evaluate_signed_ab.py` сравнивает только evidence records, у которых валидна HMAC-подпись, `accepted=true` и совпадает `protocol_fingerprint`. Fingerprint включает task-manifest SHA-256, model/provider и workspace policy. При mismatch evaluator сохраняет диагностические records, но каждый metric получает `comparable=false`; ranking не создаётся. Metric `observed` допускается только внутри record, а top-level status остаётся ограниченным (`passed`, `failed`, `unsupported`, `not_run`).


## Reproducible local signed fixture lane

` scripts/run_local_signed_ab_fixture.py` выполняет только plumbing lane: создаёт deterministic task-manifest, два synthetic pinned specs (`hermes` и `opencode`), подписывает их, прогоняет ingestion и unified evaluator и сохраняет `noesis.local-signed-ab-fixture.v1`. В lane не запускаются внешние процессы, модели, shell commands или пользовательские credentials. Comparable result в этом lane доказывает корректность ingestion/evaluation pipeline, но не качество Hermes/OpenCode и не внешний A/B ranking.


## Connector-neutral execution adapter

` scripts/pinned_runner_adapter.py` является единственным optional execution boundary для pinned external runners. По умолчанию выполнение запрещено; требуется явный `approval=True`. Команда передаётся только как argv-массив с `shell=False`, workspace должен существовать и иметь policy `disposable/deny/credentials=absent`, environment ограничивается `PATH` и `NOESIS_EXTERNAL_RUNNER`, timeout возвращается как структурированный failed outcome. Adapter redacts credential-like output и не исполняет model-generated code в core control plane.


## Operator runbook bridge

` scripts/run_external_lane.py` связывает pinned spec с adapter и evidence pipeline в безопасном режиме. Без `--execute` создаётся только plan с `execution=not_started`; `--execute` без `--approve` возвращает `denied/not_run`. Только `--execute --approve` может начать процесс, после чего результат фиксируется как structured `started` outcome с status, return code, timeout и redacted output.

Для Hermes/OpenCode/DeepSeek Harness оператор сначала должен получить exact immutable revision, model/provider, task-manifest SHA-256, protocol fingerprint, required seed digest и disposable workspace, затем выполнить strict manifest validation, capability-aware dry-run и проверить plan. Нельзя подставлять floating revision, shell string, shared workspace, credentials или неподтверждённый executable. Approval должен быть явно связан с argv, revision, fingerprint и workspace policy. Публикация evidence выполняется отдельным ingestion/signing шагом.


## Structured outcome → evidence

`outcome_to_result()` преобразует только structured adapter outcome в canonical runner result. `execution=started` создаёт observed `task_success`; `denied`, `not_started` и иные неисполненные outcomes создают explicit `status=not_run` и только not_run metrics. Unified evaluator дополнительно требует минимум два accepted signed records со статусом не `not_run` и общим protocol fingerprint; поэтому denied/not_run records никогда не превращаются в external comparison.


## Local A/B release report

` scripts/build_local_ab_release_report.py` собирает `noesis.local-ab-release.v1` из fixture lane. Report содержит task-manifest SHA-256, source-result digests каждого evidence, flag `external_processes_started`, unified evaluation, три hash-linked audit events (`fixture_created`, `evidence_ingested`, `evaluation_completed`) и HMAC integrity envelope. `verify_report()` проверяет sequence, previous hash, event hash и подпись. Report является reproducible local plumbing evidence и не заявляет реальный Hermes/OpenCode execution.
