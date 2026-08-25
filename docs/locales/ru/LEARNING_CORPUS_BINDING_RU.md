# Learning Corpus Binding — русская локализация

Это supplemental-описание English primary contract для Gate 1 evidence-corpus provenance binding в [`noesis_harness/learning_corpus_binding.py`](../../../noesis_harness/learning_corpus_binding.py): tamper-evident детерминированный envelope, пиннящий promotion proposal к digest отчёта `evaluate_corpus_v2`. English primary contract: [`LEARNING_CORPUS_BINDING.md`](../../LEARNING_CORPUS_BINDING.md).

## Purpose

Review proposals обязаны нести evidence-corpus provenance, верифицируемую независимо от proposer'а. Binding — integrity envelope над canonical JSON: он фиксирует, к какому corpus report (по schema version и digest) привязан proposal, и fail-closed отвергает tampering, нарушение формы и mismatch отчёта. Deterministic core rule соблюдается: wall clock не читается без явной инъекции caller'ом; binding без injected clock байт-стабилен между запусками и машинами.

## Binding schema

`bind_corpus_evidence` возвращает dict ровно с этими ключами (`bound_at_unix` и `max_age_seconds` опциональны, остальное required):

| Ключ | Содержимое | Чем пиннится |
|---|---|---|
| `schema_version` | Всегда `noesis.learning-corpus-binding.v1`. | Константа модуля. |
| `corpus_schema_version` | Должен равняться schema v2 corpus (`noesis.memory-quality-corpus.v2`). | Валидируется по константе corpus-модуля. |
| `corpus_report_digest` | `sha256:` + 64 hex из `report_digest` отчёта. | Shape-валидация, cross-check при verify с переданным отчётом. |
| `subject.kind` | Всегда `promotion_proposal`. | Закрытый словарь. |
| `subject.proposal_id` | Safe id `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}`. | Regex-валидация fail-closed. |
| `subject.skill_digest` | Content digest proposal'а под redaction-safe именем ключа. | Строка с лимитом длины. |
| `subject.provenance_digest` | Provenance digest proposal'а. | Строка с лимитом длины. |
| `bound_at_unix` | Присутствует только при injected clock. | Обязан быть finite и неотрицательным. |
| `max_age_seconds` | Freshness policy; требует `bound_at_unix`. | Обязан быть finite и положительным. |
| `binding_digest` | sha256 над canonical binding без этого ключа. | Пересчитывается и сравнивается через `hmac.compare_digest`. |

## Module contract

- `bind_corpus_evidence(proposal_builder_or_proposal, corpus_report, *, max_age_seconds=None, clock=None)` принимает `PromotionProposal`, dataclass/mapping с полями `proposal_id`, `content_digest`, `provenance_digest`, либо zero-arg callable, возвращающий любое из этого. Исключения builder'а всплывают как `subject_builder_failed`, никогда не молча.
- Default output без timestamp и байт-стабилен: `bound_at_unix` появляется только при injected clock; `max_age_seconds` требует clock (`clock_required_for_max_age`) — freshness policy нельзя подделать на timeless binding.
- `verify_corpus_binding(binding, *, corpus_report=None)` fail-closed и никогда не raises: закрытый словарь ключей (неизвестный extra key отклоняется, даже если атакующий пересобрал digest), проверки schema, формы subject, integrity digest над canonical JSON через `hmac.compare_digest`, опциональный mismatch-check против переданного отчёта.
- `attach_to_telemetry(telemetry_payload, binding)` аттачит только верифицированный binding под `corpus_binding`; idempotency conflict policy fail-closed — существующий ключ поднимает `telemetry_binding_conflict` вместо перезаписи.
- Имена subject-ключей сознательно redaction-safe: `PromotionTelemetry._redact` маскирует любой ключ со словом "content", поэтому canonical поле `content_digest` записывается как `skill_digest`, сохраняя verbatim-верифицируемость binding после redaction телеметрии.
- [`noesis_harness/promotion_integration.py`](../../../noesis_harness/promotion_integration.py), метод `PromotionIntegration.propose`, принимает опциональный keyword-only `corpus_binding`: binding верифицируется fail-closed ДО pipeline side effect, затем аттачится аддитивно в telemetry event `promotion_proposed`.

## Typed values and error codes

Коды `LearningCorpusBindingError`: `corpus_report_invalid`, `subject_invalid`, `subject_builder_failed`, `subject_proposal_id_invalid`, `subject_digests_invalid`, `clock_not_callable`, `clock_value_invalid`, `max_age_seconds_invalid`, `clock_required_for_max_age`, `telemetry_payload_invalid`, `telemetry_binding_conflict`, `binding_verification_failed`.

Константы схемы: `BINDING_SCHEMA_VERSION = noesis.learning-corpus-binding.v1`; telemetry key `TELEMETRY_BINDING_KEY = corpus_binding`. Верификация boolean; builder'ы поднимают типизированные ошибки.

## Wiring status

Интегрирован keyword-only в `PromotionIntegration.propose` в [`noesis_harness/promotion_integration.py`](../../../noesis_harness/promotion_integration.py): невалидный binding прерывает propose до любых изменений pipeline state; валидный едет в payload telemetry `promotion_proposed` под `corpus_binding` и переживает redaction verbatim.

## Related tests

- [`tests/test_learning_corpus_binding.py`](../../../tests/test_learning_corpus_binding.py) — round-trip bind/verify против реального corpus report v2, эквивалентность builder/mapping/direct subjects, fail-closed набор невалидных входов, детерминизм с clock и без, tamper detection (digest, поля payload, чужие отчёты, forged extra keys), conflict policy telemetry attach, интеграция `PromotionIntegration.propose` включая failure до side effect.

## Provenance

Заимствованные паттерны: governance receipt patterns agentmemory — tamper-evident canonical JSON + sha256 integrity envelope с fail-closed verification (`hmac.compare_digest`), как уже портировано в learning_promotion/promotion_integration; fail-closed verification discipline deepseek-harness, зеркалимая в `memory_quality_corpora.verify_case_provenance`. Без LLM, без сети, без wall clock без инъекции.

## Claim boundary

Верифицированный binding подтверждает только то, что названный proposal был ассоциирован с corpus report указанного digest на момент bind и что envelope не изменён с тех пор. Он не подтверждает качество внешней модели, не перезапускает corpus и не валидирует сам skill content; enforcement свежести через `max_age_seconds` — ответственность verifier'а.
