# Work Product Commit Markers — русская локализация

Это supplemental-описание English primary contract для durable append-only ledger явных task commit markers (`WorkProductCommitMarkerLedger` в [`noesis_harness/work_product_benchmark.py`](../../../noesis_harness/work_product_benchmark.py)) и его binding в governed multi-agent workflow ([`noesis_harness/multi_agent_workflow.py`](../../../noesis_harness/multi_agent_workflow.py)). English primary contract: [`WORK_PRODUCT_COMMIT_MARKERS.md`](../../WORK_PRODUCT_COMMIT_MARKERS.md).

## Purpose

Commit marker — типизированная content-addressed запись вида: «этот конкретный reviewed work product закоммичен по этой задаче этим агентом под этим merge authorization». Ledger превращает утверждение в replayable durable fact, который переживает restart процесса и независим от coordination event log (и может с ним cross-check).

## Marker identity and storage

| Требование | Acceptance rule |
|---|---|
| Поля маркера | `product_id`, `task_id`, `agent_id`, `workspace_id`, `base_snapshot_id`, `head_snapshot_id`, `artifact_digest`, `authorization_digest`, `schema_version` = `noesis.work-product-commit-marker.v1`. |
| Идентичность | `marker_id` = `"marker:" + sha256(canonical JSON всех полей)[:32]`; детерминирован и пересчитываем из payload. |
| Хранение | Append-only JSONL через [`noesis_harness/event_store.py`](../../../noesis_harness/event_store.py); event type `work_product_commit_marker`; `event_id == marker_id`. |
| Инвариант | Не более одного маркера на `product_id`, навсегда. |

## Workflow binding

- `MultiAgentWorkProductLoop.commit()` строит маркер из envelope + `MergeAuthorization.authorization_digest` и пишет его **до** перевода задачи в `committed` и до append `work_product_committed`. Любая ошибка ledger поднимает `WorkProductError`; задача остаётся в `review`, commit event отсутствует.
- `resume()` добавляет проекцию `commit_markers` (`{"count", "last_marker_id"}`) при подключённом ledger; повторное открытие с тем же path даёт идентичную проекцию.
- Ledger опционален (`marker_ledger=None`) — прежнее поведение без ключа `commit_markers`.

## Typed statuses

`CommitMarkerRecord(status, marker_id, duplicate)`:

| Status | Duplicate | Семантика |
|---|---|---|
| `committed` | `False` | Первая durable запись маркера. |
| `replayed` | `True` | Идентичный double-send поглощён как no-op; новая строка не пишется. |

Коды ошибок: `<field>_required`, `unsupported_commit_marker_schema`, `commit_marker_payload_invalid`, `commit_marker_type_required`, `commit_marker_conflict`, `commit_marker_tampered`, `ledger_unexpected_event:<type>`, `ledger_conflict_on_replay`.

## Idempotency and fail-closed semantics

- Повторная отправка идентичного маркера возвращает `replayed`; физически существует одна строка лога.
- Повторный commit того же `product_id` с любым отличающимся полем — `commit_marker_conflict` (в процессе и на replay). Расхождение отклоняется, никогда не переписывается.
- На replay fail-closed: неожиданный event type, некорректный/чужой payload, несовпадение сохранённого `event_id` с пересчитанным `marker_id` (`commit_marker_tampered`), два разных маркера одного продукта.
- Ремонтируется только torn final line (краш во время append); повреждение до tail фатально.
- `verify_integrity()` перечитывает весь лог и валидирует каждую запись; возвращает `{"ok": True, "markers", "records", "schema_version"}` или raises.

## Provenance

Заимствованные паттерны: LoopX append-only fingerprint-idempotent event log через `event_store.py`; agentmemory governance conflict handling (идентичный resend = replay, расхождение отклоняется, без перезаписи); deepseek-harness bounded deterministic rubric для соседнего `WorkProductBenchmarkEvaluator`.

## Related tests

- [`tests/test_work_product_gate4_gap.py`](../../../tests/test_work_product_gate4_gap.py) — absorption double-send, replay после restart, repair torn tail, отклонение tampering mid-file, чужие event/payload, integrity report, Gate 4 locks уровня loop.
- [`tests/test_multi_agent_workflow_markers.py`](../../../tests/test_multi_agent_workflow_markers.py) — binding commit/resume, инвариант «ровно один маркер», forged authorization fail-closed с задачей в `review`, стабильность resume-проекции при reopen, legacy-path без ledger.
- [`tests/test_work_product_benchmark.py`](../../../tests/test_work_product_benchmark.py) — детерминизм метрик sibling evaluator и fail-closed валидация входов.

## Claim boundary

Evidence только локальный и детерминированный: SHA-256 identity над canonical JSON и replay-проекция локального JSONL лога. Верифицированный ledger подтверждает, что маркеры записаны и локально перепроверяемы; он не доказывает внешнее применение merge (`files_applied` остаётся `False`), намерения reviewer или состояние внешних систем. LLM, сеть, randomness и wall clock в записи и верификации не участвуют.
