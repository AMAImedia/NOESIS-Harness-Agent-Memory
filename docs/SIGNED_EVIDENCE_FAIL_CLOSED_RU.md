# Fail-Closed signed evidence

## Назначение

Evidence внешнего runner-а является integrity envelope для явно подтверждённого операторского workflow. Это не public-key release signature и не доказательство фактического запуска внешней системы, если запись не содержит разрешённый execution и matching environment.

## Правила приёма

`ingest_runner_result.py` принимает результат только после проверки result contract, pinned identity, disposable workspace, argv, metrics, credential holdout и protocol fields. Envelope подписывается runtime HMAC key, который не сохраняется в документе.

`verify_evidence()` теперь fail-closed для несловарных envelope, отсутствующих полей, непустого `errors`, плохих hash-значений, неверной подписи, короткого ключа, неaccept-нутой записи и неправильного контейнера metrics. Для hostile input возвращается `False`, а не исключение.

| Условие | Результат |
|---|---|
| Валидный accepted envelope и matching key | `True` |
| Отсутствует или неверна signature | `False` |
| Поле отсутствует или имеет плохой формат | `False` |
| `accepted` не равен точно `true` | `False` |
| Есть ingestion errors | `False` |
| External runner не запущен | Валидный signed `not_run`, но не ranking |
| Fixture-only simulated result | Явно simulation-only; не native/external evidence |

## Граница доказательства

Signed evidence подтверждает целостность записи относительно controlled key. Это не доказывает, что ключ принадлежит внешнему vendor, что модель подлинная или что использовался native host. Для comparative evaluation дополнительно нужны одинаковый protocol fingerprint, минимум две accepted executable records, exact revisions и explicit operator approval.

Нормативная English-версия: [`SIGNED_EVIDENCE_FAIL_CLOSED.md`](SIGNED_EVIDENCE_FAIL_CLOSED.md).
