# Protocol Leakage Holdouts — русская локализация

Это supplemental-описание English primary contract для `ProtocolLeakageSuite` в [`noesis_harness/protocol_leakage_holdouts.py`](../../../noesis_harness/protocol_leakage_holdouts.py): детерминированные protocol/provider leakage holdouts поверх реальных parallel executor lanes. English primary contract: [`PROTOCOL_LEAKAGE_HOLDOUTS.md`](../../PROTOCOL_LEAKAGE_HOLDOUTS.md).

## Purpose

Suite доказывает гигиену protocol boundary в multi-agent execution path. Каждый probe идёт через живой `SafeParallelExecutor` lane fan-out ([`noesis_harness/parallel_agent.py`](../../../noesis_harness/parallel_agent.py)); storage, recall и coordination LLM не вызывают. Четыре фиксированных случая:

| Case id | Probe | Detector |
|---|---|---|
| `event_sink_redaction` | Отравленный callback output (canary, абсолютный workspace path, значение окружения) не должен попасть в `event_sink` payloads; чистые lanes не содержат ключа `error` и дают ровно два события на lane. | `redaction_violation` над key envelope плюс поиск запрещённых подстрок. |
| `audit_error_isolation` | Внутренний token падающей lane виден только в её собственном `result.error`; executor audit trail и peer results чисты; peers остаются `passed`. | Рекурсивный value-tree needle search по audit и peer результатам. |
| `result_envelope_typing` | `AgentLaneResult` пересекает границу только объявленными типизированными полями с корректными типами; типизированные output и error сохраняются точно. | `envelope_violation`. |
| `cross_session_event_scoping` | Два последовательных run на одном shared executor с разными session ids; внедрённый foreign-session marker доходит до lane outputs, но не до events; события второго run не содержат ни foreign marker, ни session id первого run. | `scoping_violation`. |

## Typed contracts

- `SINK_ALLOWED_KEYS = {kind, session_id, task_id, agent_id, error}` — единственные ключи, разрешённые через event-sink boundary.
- `RESULT_REQUIRED_KEYS = {status, task_id, agent_id, workspace, output, error}` — подмножество объявленных полей `AgentLaneResult`.
- `LANE_RESULT_STATUSES = {passed, failed, blocked, cancelled}` — закрытый словарь статусов lane results.
- `ProtocolLeakageResult(case_id, passed, observed)` — один исход на case; `observed` = `"clean:..."` / `"scoped:..."` при pass либо точный violation code.

Словарь violation-кодов: `payload[i].extra_keys=...`, `payload[i].forbidden_value=...`, `result[i].extra_fields=...`, `result[i].missing_fields=...`, `result[i].status_unknown=...`, `result[i].{task_id,agent_id,workspace,error,attempts,recovered}_untyped`, `event[i].session_mismatch=...`, `event[i].foreign_session_marker=...`.

## Fail-closed semantics

- Любое неожиданное исключение внутри case классифицирует его как failed с observed `unexpected_exception:<Type>`; pass никогда не присваивается.
- Опциональный `executor_factory` подменяет executor для негативного тестирования simulated leaky providers (например, executor, добавляющий workspace root в каждый payload); suite обязан его обнаружить.
- Поиск подстрок идёт прямо по JSON-like value trees, а не по сериализованным blob'ам: Windows backslash пути ловятся, несмотря на экранирование внутри JSON-строки.
- `summary()` отдаёт `schema_version` (`noesis.protocol-leakage.v1`), исходы по cases, `total`, `passed`, `failed`, `pass_rate`; результаты детерминированы между запусками.

## Provenance

Заимствованные паттерны: нормы redaction observability Hermes/OpenCode (минимальные типизированные event envelopes, sinks без секретов); fail-closed evidence handling deepseek-harness; дисциплина fixed-corpus negative/positive holdouts из [`noesis_harness/isolation_holdouts.py`](../../../noesis_harness/isolation_holdouts.py) (детерминированные leakage cases линии agentmemory).

## Related tests

- [`tests/test_protocol_leakage_holdouts.py`](../../../tests/test_protocol_leakage_holdouts.py) — детерминизм all-pass, схема summary, минимализм live event-sink payload, негативная инъекция leaky executor, unit-violations каждого detector'а (лишние ключи/canary, внедрённое поле, чужая session), broken factory fail-closed по всем cases.

## Claim boundary

Evidence только локальный и детерминированный: фиксированные canaries, временные локальные директории и in-process выполнения lanes, оцениваемые чистыми substring/type проверками. Пройденный summary подтверждает гигиену protocol boundary данного code path на данной машине в данном pinned состоянии кода; это не внешний security audit, не provider-level гарантия и не evidence о каких-либо удалённых системах. LLM, сеть и wall clock в оценке не участвуют.
