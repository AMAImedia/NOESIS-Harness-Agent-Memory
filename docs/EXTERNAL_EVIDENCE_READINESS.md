# External Evidence Readiness Matrix

## Contract

`scripts/external_evidence_readiness.py` emits `noesis.external-evidence-readiness.v1` for the Hermes, OpenCode, and DeepSeek Harness lanes. The matrix is connector-neutral and never launches a third-party executable.

Each lane receives exactly one readiness status:

| Status | Meaning |
|---|---|
| `passed` | Signed evidence, pinned identity, environment digest, receipt identity, and protocol checks passed. This is ingestion readiness, not a quality or superiority claim. |
| `not_run` | No exact revision is pinned, or execution was explicitly not started/denied. It is not a pass, failure, or zero score. |
| `blocked` | A pinned lane has missing evidence, duplicate records, stale receipt, revision/environment mismatch, invalid signature, or protocol conflict. |
| `unsupported` | The lane explicitly reports that the required capability or execution mode is unsupported. It is not converted to a failure score. |

## Required checks

The matrix validates exact revision, `environment_digest`, deterministic `receipt_id`, HMAC envelope verification, duplicate system records, duplicate receipt IDs across lanes, and shared `protocol_fingerprint`. When the manifest pins a protocol fingerprint, every accepted lane record must match it. It emits lane checks and reasons, global checks, a deterministic `matrix_digest`, `comparative_ready`, and an explicit `native_or_external_execution_claim` boolean.

Comparative readiness requires at least two `passed` executable records with one shared protocol fingerprint and no global conflict. A matrix may be `passed` while the underlying external agent run remains outside this repository only when the signed evidence is supplied by an approved operator workflow. The current repository artifact is intentionally `not_run`: all three manifest revisions are empty and `native_or_external_execution_claim` is `false`. The pinned operator orchestrator embeds the same readiness preflight before it can consider any external execution command.

## Current artifact

The machine-readable snapshot is [`EXTERNAL_EVIDENCE_READINESS_MATRIX.json`](EXTERNAL_EVIDENCE_READINESS_MATRIX.json). Its current lane statuses are `hermes=not_run`, `opencode=not_run`, and `deepseek_harness=not_run` because exact immutable revisions have not been supplied.

The Russian supplemental localization is available at [`locales/ru/EXTERNAL_EVIDENCE_READINESS_RU.md`](locales/ru/EXTERNAL_EVIDENCE_READINESS_RU.md).
