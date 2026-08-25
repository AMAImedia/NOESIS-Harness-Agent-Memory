# Evidence Projection — русская локализация

Это supplemental-описание English primary contract для fail-closed evidence projection в [`noesis_harness/evidence_projection.py`](../../../noesis_harness/evidence_projection.py): детерминированная read-only digest-поверхность над локально закоммиченными evidence-артефактами для operator plane ([`noesis_harness/health_server.py`](../../../noesis_harness/health_server.py)). English primary contract: [`EVIDENCE_PROJECTION.md`](../../EVIDENCE_PROJECTION.md).

## Purpose

Operator plane должен видеть, существуют ли закоммиченные локальные evidence-артефакты и проходят ли они проверку целостности — без выполнения, мутаций и доверия непроверенному документу. `project_evidence()` читает [`docs/MULTI_AGENT_WORKLOAD_EVIDENCE.json`](../../MULTI_AGENT_WORKLOAD_EVIDENCE.json) и [`docs/MEMORY_QUALITY_EVIDENCE.json`](../../MEMORY_QUALITY_EVIDENCE.json), верифицирует integrity digest workload-документа, показывает report digest'ы memory-quality corpus как present-or-absent и fail-closed: отсутствующий или битый файл деградирует в unavailable-статус вместо исключения. Правило детерминированного ядра соблюдено: без LLM, сети и wall clock; projection зависит только от содержимого файлов и не содержит timestamps.

## Схема projection (`noesis.evidence-projection.v1`)

`project_evidence(workload_path=None, memory_quality_path=None)` возвращает:

| Ключ | Содержимое | Примечание |
|---|---|---|
| `schema_version` | Всегда `noesis.evidence-projection.v1`. | Константа модуля `EVIDENCE_PROJECTION_SCHEMA`. |
| `claim_boundary` | Всегда `committed_local_evidence_read_only_fail_closed`. | Закрытый словарь, встроен в каждую projection. |
| `workload_evidence` | Статус-объект документа workload evidence. | См. ниже. |
| `memory_quality_digests` | Список digest-presence записей из memory-quality evidence. | По записи на каждый sub-report `adversarial_corpus_*` (сортировка по ключу) плюс одна top-level запись. |

### `workload_evidence`

| Поле | Available | Unavailable |
|---|---|---|
| `schema_version` | Собственный `schema_version` документа (напр. `noesis.workload-evidence.v1`). | `""`, либо значение документа, если это строка, даже при отказе. |
| `available` | `True` — файл распарсен, JSON object, required поля на месте. | `False` — всегда. |
| `digest_verified` | `True`, только если сохранённый `output_digest` совпал с пересчитанным canonical digest. | `False` — всегда. |
| `output_digest` | Сохранённый `output_digest` (`sha256:` + 64 hex). | `""`, либо сохранённое значение, если это непустая строка, даже при отказе. |
| `reason` | `""` при верификации; иначе `output_digest_mismatch`. | Типизированный код отказа; никогда не пустой. |

Доступный, но неверифицированный документ (`reason = "output_digest_mismatch"`) показывается, а не скрывается: operator видит сигнал tamper без каких-либо claims от его имени.

### Записи `memory_quality_digests`

Каждая запись — `{corpus_schema_version, report_digest, digest_present}`:

- На sub-report (`adversarial_corpus_*`, отсортированы по ключу): `corpus_schema_version` — его `schema_version`; `report_digest` переносит его `report_digest`, если это непустая строка; `digest_present` истинен только тогда.
- Финальная запись: top-level `schema_version` документа с `report_digest = ""` и `digest_present = false`.

## Правило пересчёта canonical digest

`digest_verified` пересчитывает sha256 над canonical JSON payload без ключа `output_digest` и сравнивает с сохранённым значением через `hmac.compare_digest` (constant-time):

```python
unsigned = {key: value for key, value in payload.items() if key != "output_digest"}
recomputed = "sha256:" + hashlib.sha256(
    json.dumps(unsigned, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
).hexdigest()
verified = hmac.compare_digest(recomputed, stored)
```

Это тот же байт-стабильный digest, который эмитят генераторы evidence: перегенерированный артефакт верифицируется без изменений, а любое однобайтовое изменение документа ломает верификацию.

## Типизированный словарь причин

`load_workload_evidence` никогда не бросает исключений; отказы отображаются в закрытый набор reason-кодов: `path_not_provided`, `file_missing`, `path_invalid`, `path_is_directory`, `file_unreadable`, `json_invalid` (ошибка декодирования или парсинга JSON), `payload_not_object` (валидный JSON, но не object), `required_field_missing` (отсутствует/пуст `schema_version` или `output_digest`) и `output_digest_mismatch` после неудачной верификации. Каждый unavailable-результат несёт `available = false`, `digest_verified = false` и непустую типизированную причину.

`load_memory_quality_digests` тоже не бросает: отсутствующий, нечитаемый, невалидный или не-object документ даёт пустой список, а отсутствующий или пустой digest sub-report честно показывается как `digest_present = false`, а не выпадает или выдумывается. Аттестуется только наличие digest; верификация corpus digest требует corpus fixtures и здесь вне scope.

## Integration

[`HealthServer.operator_snapshot`](../../../noesis_harness/health_server.py) принимает опциональный keyword-only параметр `evidence_projection`: `None` (по умолчанию) оставляет snapshot неизменным — ключ отсутствует, существующие потребители видят те же байты; переданная projection вставляется дословно под `evidence_projection`. Projection строит вызывающий; сервер сам файлы evidence не читает.

## Related tests

- [`tests/test_evidence_projection.py`](../../../tests/test_evidence_projection.py) — реальный закоммиченный workload evidence верифицируется против сохранённого digest; однократно испорченная копия даёт `output_digest_mismatch`; отсутствующие и битые файлы fail-closed с типизированными причинами; записи memory-quality digest (два corpus sub-report плюс top-level) совпадают с pinned evidence-документом; повторные projections байтово равны; дефолты безопасны при отсутствии путей; `operator_snapshot` по умолчанию не содержит ключ и встраивает переданную projection дословно.

## Provenance

Заимствованные паттерны: fail-closed verification deepseek-harness (отсутствующий/битый вход деградирует в типизированный unavailable-статус вместо исключения, `hmac.compare_digest` над canonical JSON); read-only projections LoopX (детерминированный view в стиле replay над закоммиченным состоянием без его мутации). Canonical-JSON верификация digest следует линии signed report bundle / lifecycle audit ingestion, уже портированной в репозитории; конвенция bounded snapshot следует паттерну HealthServer `evidence_aggregate`.

## Claim boundary

Projection — read-only аттестация ЛОКАЛЬНЫХ закоммиченных файлов на момент чтения: она утверждает, что названные документы существуют, парсятся и что их integrity digests совпадают с содержимым на этой машине. Она не перезапускает workload'ы, не валидирует то, что документы утверждают о выполнениях, не верифицирует corpus digests и не является внешним или сравнительным evidence в любом смысле.
