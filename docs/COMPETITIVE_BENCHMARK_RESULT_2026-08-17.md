# Competitive benchmark result — 2026-08-17

## Scope

This report covers the local contract lane only. It does not claim to execute Hermes or OpenCode, and it does not replace a same-task external A/B run. The runner uses fixed NOESIS tests, explicit budgets, no model-generated code execution and no external network calls.

## Result

The contract lane completed with **10 passed, 0 failed, 0 not-run** on CPython 3.12.3 in the current sandbox. The full regression suite completed with **240 passed**. The tested surfaces include task/session state, SSE reconnect, provider invocation, Gatekeeper approval, bounded child execution, executable skills, workspaces, multi-agent claims, HTTP session API and terminal client.

| Lane | Status | Interpretation |
|---|---:|---|
| NOESIS contract primitives | 10/10 passed | Local implementation evidence |
| Full regression suite | 240/240 passed | Local reliability evidence |
| Hermes external protocol | `not_run` | No external process was started |
| OpenCode external protocol | `not_run` | No external process was started |
| Native Windows Python 3.14 | `not_run` | No Windows 3.14 runner available |
| Native macOS Python 3.14 | `not_run` | No macOS 3.14 runner available |

## Required external A/B protocol

A valid external comparison must pin exact revisions, model/provider, prompt set, context budget, tool permissions, sandbox backend, timeout, retry policy and evaluator rubric. Each system must run in a disposable workspace. Metrics must include task success, patch correctness, approval violations, unauthorized egress, secret exposure, recovery after kill/timeout, token/latency budget and human review burden. Unsupported or unavailable features must be reported as `not_run`, never as zero failures.

## References

[1]: https://opencode.ai/docs/agents/ "OpenCode agents documentation"
[2]: https://opencode.ai/docs/tools/ "OpenCode tools documentation"
[3]: https://github.com/NousResearch/hermes-agent "Hermes Agent repository"
