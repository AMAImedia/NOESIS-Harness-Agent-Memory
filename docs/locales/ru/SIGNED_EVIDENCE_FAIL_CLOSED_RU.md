# Fail-Closed signed evidence

## Назначение

Evidence внешнего runner-а является integrity envelope для явно подтверждённого операторского workflow. Это не public-key release signature, vendor attestation и не доказательство фактического запуска внешней системы, если запись не содержит разрешённый execution на matching environment.

## Правила приёма

`ingest_runner_result.py` принимает результат только после проверки result contract, pinned identity, disposable workspace, argv, metrics, credential holdout и protocol fields. Envelope подписывается runtime HMAC key, который не сохраняется в документе.

| Условие | Требование | Fail-closed результат |
|---|---|---|
| Schema | External result и evidence используют зафиксированные schema versions | Reject envelope |
| Pinned identity | system, revision, provider, task digest, protocol fingerprint, workspace и argv совпадают со spec | Reject envelope |
| Environment | Есть declared environment; workspace disposable; outside access denied; credentials absent | Reject envelope |
| Environment identity | Есть signed `environment_digest` от canonical environment | Reject missing/malformed digest |
| Receipt identity | Есть deterministic `receipt_id` от lane, revision, fingerprint, source digest и environment digest | Reject stale/mismatched receipt |
| Metrics | Непустой mapping с допустимыми statuses | Reject malformed metrics |
| Credential holdout | Нет token/password/secret/bearer/credential-like content | Reject envelope |
| Signature | Canonical unsigned envelope подписан HMAC-SHA256 | Reject missing/malformed/mismatched signature |

`accepted` должен быть именно boolean `true`, а `errors` — пустым списком. Запись с `accepted=false` может быть подписана для audit, но не участвует в comparative evaluation.

`verify_evidence()` fail-closed для несловарных envelope, отсутствующих полей, неправильной schema, непустого `errors`, плохих hash-значений, неверной подписи, короткого ключа, stale receipt, неaccept-нутой записи и неправильного контейнера metrics. Для hostile input возвращается `False`, а не исключение.

| Условие | Результат |
|---|---|
| Валидный accepted envelope и matching key | `True` |
| Отсутствует или неверна signature | `False` |
| Поле отсутствует или имеет плохой формат | `False` |
| `accepted` не равен точно `true` | `False` |
| Есть ingestion errors | `False` |
| External runner не запущен или denied | Валидный signed `not_run`, но не ranking |
| Missing exact revision | `not_run` |
| Revision pinned, но evidence отсутствует | `blocked` |
| Duplicate system record | `blocked` |
| Revision/environment mismatch | `blocked` |
| Protocol fingerprint conflict | `blocked`; comparative readiness false |
| Unsupported lane | `unsupported`; не превращается в zero score |
| Fixture-only simulated result | Явно simulation-only; не native/external evidence |

## Unified readiness matrix

`scripts/external_evidence_readiness.py` создаёт `noesis.external-evidence-readiness.v1`. Для Hermes, OpenCode и DeepSeek Harness каждая lane получает ровно один статус: `passed`, `not_run`, `blocked` или `unsupported`. Matrix содержит checks, reasons, accepted receipt IDs, protocol conflicts, deterministic matrix digest и `comparative_ready`.

`passed` в readiness matrix означает только, что ingestion и identity checks прошли. Это не означает, что внешний агент превосходит NOESIS или что orchestrator фактически запускал внешнюю систему.

## Граница доказательства

Signed evidence подтверждает целостность записи относительно controlled key. Это не доказывает, что ключ принадлежит внешнему vendor, что модель или binary подлинные, что child process был изолирован или что использовался native host. Для comparative evaluation дополнительно нужны exact immutable revisions, одинаковые task-manifest и protocol fingerprints, минимум две accepted executable records, matching environment evidence, disposable workspaces и explicit operator approval.

Нормативная English-версия: [`SIGNED_EVIDENCE_FAIL_CLOSED.md`](../../SIGNED_EVIDENCE_FAIL_CLOSED.md).
