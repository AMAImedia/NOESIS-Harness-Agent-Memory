# Memory Quality Corpora v2 — русская локализация

Это supplemental-описание English primary contract для pinned adversarial memory-quality corpus (Gate 5, broader independent corpora) в [`noesis_harness/memory_quality_corpora.py`](../../../noesis_harness/memory_quality_corpora.py). Документ описывает module contract; wiring runner'а отслеживается отдельно (см. Wiring status). English primary contract: [`MEMORY_QUALITY_CORPUS_V2.md`](../../MEMORY_QUALITY_CORPUS_V2.md).

## Purpose

Детерминированный stdlib-only fixture corpus, расширяющий покрытие memory-quality без изменений core evaluator ([`noesis_harness/memory_quality.py`](../../../noesis_harness/memory_quality.py)). Corpus — чистые константы: без wall clock и randomness; report digest байт-стабилен между запусками и машинами.

## Corpus composition

`ADVERSARIAL_CORPUS_V2` пиннит 12 cases в 8 категориях на двух sessions (`v2-session-alpha`, `v2-session-beta`) с жёстким бюджетом 64 токена:

| Категория | Cases | Что пиннит |
|---|---|---|
| `temporal_inversion_pair` | `v2-temporal-inversion-early`, `-late` | Корректный порядок даёт 1.0; инвертированный late case обязан дать `temporal_order = 0.0` при recall 1.0. |
| `duplicate_attribution` | `v2-duplicate-attribution` | Дубликат attribution id не должен инфлировать precision: честная precision 0.5; флаг inflation срабатывает, если evaluator всё же вернул 1.0. |
| `near_duplicate_query` | `v2-near-duplicate-query-primary`, `-variant` | Оба near-duplicate варианта по отдельности держат recall 1.0 и attribution precision 1.0. |
| `budget_edge_long_trace` | `v2-budget-edge-exact`, `-overrun` | `used == budget` уважает hard cap; `used == budget + 1` помечается `budget_respected = False` — детектируется, никогда не проходит молча. |
| `conflict_with_provenance` | `v2-conflict-provenance` | Смоделированное неверное conflict resolution (`conflict_resolution = 0.0`) сохраняет per-case verifiability provenance. |
| `decay_floor_boundary` | `v2-decay-floor-boundary` | At-floor запись выживает ровно на floor; sub-floor raw decay вытесняется из retention, оставаясь required; retention 0.5. |
| `leakage_decoy` | `v2-leakage-decoy` | Cross-scope leak decoy даёт `leakage_free = False` при ненарушенной attribution precision 1.0. |
| `cross_session_decoy_reuse` | `v2-cross-session-decoy-alpha`, `-beta` | Реальный experience reuse даёт recall 1.0; decoy reuse — recall 0.0. |

Каждый case имеет запись в `EXPECTED_V2`; `evaluate_corpus_v2` фиксирует любое расхождение как `expectation_violations`.

## Module contract

- `AdversarialCorpusCaseV2` — frozen dataclass с `payload()` (canonical JSON dict), `provenance_digest()` (`sha256:` над canonical payload) и проекциями `to_memory_quality_case()` / `to_trajectory_step()` в типы core evaluator.
- `build_adversarial_corpus_v2()` пересобирает кортеж и fail-closed на дубликатах case id (`duplicate_corpus_case_id`).
- `project_decay_strengths(base_strengths, periods)` применяет экспоненциальный decay с clamp на `Memory.DECAY_FLOOR` (0.1) из [`noesis_harness/memory.py`](../../../noesis_harness/memory.py), зеркаля decay-модель хранилища.
- `verify_case_provenance(case)` регенерирует payload чисто из evaluator-bound полей и сравнивает digest'ы; gap wrapper нужен, потому что core `MemoryQualityCase` не несёт provenance binding.
- `_check_decay_boundary` fail-closed валидирует арифметику decay fixture (`decay_fixture_invalid` при нарушении формы).
- `evaluate_corpus_v2(adapter_factory)` записывает все cases через adapter по sessions, оценивает через `MemoryQualityEvaluator` и возвращает отчёт: `schema_version` (`noesis.memory-quality-corpus.v2`), `per_case` (метрики плюс `provenance_verified`, `decay_floor_boundary_respected`, `expectation_violations`), aggregate metrics, `duplicate_attribution_inflation_detected`, `categories`, `session_ids`, встроенная строка `claim_boundary`, байт-стабильный `report_digest`.
- Adapter contract: фабрика обязана вернуть объект с callable `record_trajectory(session_id, steps)` и `evaluate_sessions(sessions)`; reference implementation — `DurableMemoryQualityAdapter`. Нарушения поднимают `adapter_factory_invalid` / `adapter_contract_invalid`.

## Typed values and error codes

Коды `MemoryQualityCorpusError`: `duplicate_corpus_case_id`, `adapter_factory_invalid`, `adapter_contract_invalid`, `decay_fixture_invalid`. Per-case булевы поля имеют закрытый словарь (`provenance_verified`, `decay_floor_boundary_respected`, `budget_respected`, `leakage_free`); метрики — float в [0, 1], кроме счётчиков токенов.

## Wiring status

На 2026-08-25 [`scripts/run_memory_quality_evidence.py`](../../../scripts/run_memory_quality_evidence.py) вызывает `evaluate_corpus_v2` и эмитит её отчёт аддитивно как верхнеуровневый ключ evidence `adversarial_corpus_v2` (schema evidence остаётся `noesis.memory-quality-evidence.v3`; отчёт corpus хранит свой `noesis.memory-quality-corpus.v2`). Регенерированный [`docs/MEMORY_QUALITY_EVIDENCE.json`](../../MEMORY_QUALITY_EVIDENCE.json) байт-стабилен между повторными запусками.

## Related tests

- [`tests/test_memory_quality_corpora_v2.py`](../../../tests/test_memory_quality_corpora_v2.py) — size/uniqueness/schema и покрытие категорий, байтовое равенство двух прогонов включая digest, детекция temporal-pair, честная duplicate-attribution precision, budget edge compliance, флаги provenance/decay-floor/leakage/cross-session, fail-closed невалидных adapter factory.

## Provenance

Заимствованные паттерны: pinned adversarial fixtures в стиле evalscope (версионируемый corpus, таблица ожиданий, стабильный digest); decay-floor model agentmemory (затухание силы с clamp на floor); fail-closed expectation checks deepseek-harness; формат trajectory-записей следует линии quality-trace agentmemory из `scripts/run_memory_quality_evidence.py`.

## Claim boundary

Evidence только локальный и детерминированный: pinned константы, оцениваемые локальным stdlib evaluator'ом поверх реальных durable Memory operations, открытых adapter factory. Report digest подтверждает воспроизводимость fixtures и scoring math на этой машине в данном pinned состоянии кода. Это не внешний model benchmark, не измерение качества production memory и не сравнение с другими агентами или harness'ами.
