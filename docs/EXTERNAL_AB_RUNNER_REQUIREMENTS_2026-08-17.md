# External A/B Runner Requirements

External baseline execution is an optional, approval-gated evidence lane for Hermes, OpenCode, and DeepSeek Harness. A valid run requires an exact immutable revision, task-manifest digest, protocol fingerprint, disposable workspace, credential isolation, network policy, signed receipt, and reproducible result artifact.

Missing executable, revision, host, approval, or receipt produces `not_run` or `blocked`; it must never be coerced into `passed`, `failed`, or a comparative ranking. The detailed Russian localization is available in [`EXTERNAL_AB_RUNNER_REQUIREMENTS_2026-08-17_RU.md`](EXTERNAL_AB_RUNNER_REQUIREMENTS_2026-08-17_RU.md).
