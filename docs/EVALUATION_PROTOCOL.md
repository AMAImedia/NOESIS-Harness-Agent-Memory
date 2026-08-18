# Evaluation Protocol

This document defines the normative evaluation boundary for memory, coordination, security, coding tasks, recovery, and release decisions. Machine-readable status values are English and fail closed: `passed`, `failed`, `blocked`, `not_run`, and `not_started`.

The detailed Russian localization is available in [`EVALUATION_PROTOCOL_RU.md`](EVALUATION_PROTOCOL_RU.md). The localized document explains the same contract and does not change schemas, commands, metrics, or acceptance gates.

External A/B claims require exact pinned revisions, disposable environments, reproducible task manifests, signed evidence, and explicit operator approval. Missing hosts or revisions remain `not_run` rather than being treated as failure or success.
