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
