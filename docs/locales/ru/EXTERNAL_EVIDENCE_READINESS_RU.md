# External Evidence Readiness Matrix

## Контракт

`scripts/external_evidence_readiness.py` создаёт `noesis.external-evidence-readiness.v1` для lanes Hermes, OpenCode и DeepSeek Harness. Matrix connector-neutral и не запускает third-party executable.

| Статус | Значение |
|---|---|
| `passed` | Signed evidence, pinned identity, environment digest, receipt identity и protocol checks прошли. Это ingestion readiness, а не quality/superiority claim. |
| `not_run` | Exact revision не pinned или execution явно не запускался/отклонён. Это не pass, failure или zero score. |
| `blocked` | Для pinned lane отсутствует evidence, есть duplicate record, stale receipt, revision/environment mismatch, invalid signature или protocol conflict. |
| `unsupported` | Lane явно сообщает, что требуемая capability или execution mode не поддерживается. В failure score не превращается. |

## Проверки

Matrix проверяет exact revision, `environment_digest`, deterministic `receipt_id`, HMAC envelope, duplicate system records, duplicate receipt IDs между lanes и общий `protocol_fingerprint`. Если manifest pin-ит protocol fingerprint, каждая accepted lane record обязана ему соответствовать. В output входят lane checks/reasons, global checks, deterministic `matrix_digest`, `comparative_ready` и `native_or_external_execution_claim`.

Comparative readiness требует минимум две `passed` executable records с одним protocol fingerprint и без global conflict. Текущий artifact намеренно `not_run`: все три manifest revisions пустые, а `native_or_external_execution_claim` равен `false`. Pinned operator orchestrator использует тот же readiness preflight до рассмотрения любого external execution command.

## Текущий artifact

Machine-readable snapshot: [`EXTERNAL_EVIDENCE_READINESS_MATRIX.json`](../../EXTERNAL_EVIDENCE_READINESS_MATRIX.json). Текущие статусы: `hermes=not_run`, `opencode=not_run`, `deepseek_harness=not_run`, потому что exact immutable revisions ещё не предоставлены.

Нормативная English-версия: [`EXTERNAL_EVIDENCE_READINESS.md`](../../EXTERNAL_EVIDENCE_READINESS.md).
