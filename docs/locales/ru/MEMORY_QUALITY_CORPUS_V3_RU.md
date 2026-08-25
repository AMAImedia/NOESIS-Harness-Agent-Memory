# Memory Quality Corpora v3 — русская локализация

Это supplemental-описание English primary contract для Gate 1 broader independent corpora family в [`noesis_harness/memory_quality_corpora_v3.py`](../../../noesis_harness/memory_quality_corpora_v3.py): второй adversarial memory-quality corpus, порождаемый независимой seeded-процедурой вместо hand-pinned констант. English primary contract: [`MEMORY_QUALITY_CORPUS_V3.md`](../../MEMORY_QUALITY_CORPUS_V3.md).

## Purpose

Детерминированный stdlib-only fixture corpus, генерируемый явным linear congruential generator'ом над малыми конечными таблицами. Идентичные seeds дают байт-идентичные corpus, разные seeds структурно различаются; оба свойства assert'ятся fail-closed внутри генератора. Нетронутый core evaluator ([`noesis_harness/memory_quality.py`](../../../noesis_harness/memory_quality.py)) остаётся единственным scorer'ом: без wall clock и без модуля `random`.

## Corpus composition

`generate_corpus_v3(seed=8675309, cases_per_category=2)` эмитит 8 категорий x `cases_per_category` cases (1..16 на категорию) на двух sessions `v3-c<seed>-session-alpha` и `v3-c<seed>-session-beta` с per-corpus бюджетом из [48, 80]:

| Категория | Generated shape | Что пиннит |
|---|---|---|
| `temporal_inversion_pair` | Чередование корректного/инвертированного порядка | Корректный порядок даёт 1.0; инвертированные members обязаны дать `temporal_order = 0.0` при recall 1.0. |
| `duplicate_attribution` | Дублированная attribution (2-3 копии) плюс 1-2 noise sources | Честная attribution precision ниже 1.0; флаг inflation срабатывает, если evaluator вернул 1.0. |
| `near_duplicate_query` | Own source плюс variant source с различающимися hex-токенами | Recall 1.0 и attribution precision 1.0 по отдельности против near-duplicate selections. |
| `budget_edge_long_trace` | Длинные traces 6-10 id; overruns на нечётных индексах | `used == budget` уважает hard cap; `used == budget + 1` помечается `budget_respected = False`. |
| `conflict_with_provenance` | Current vs stale source; неверное resolution на чётных индексах | Смоделированное неверное conflict resolution сохраняет per-case verifiability provenance. |
| `decay_floor_boundary` | At-floor и sub-floor base strengths, periods 1-2, multipliers 0.5/0.75 | At-floor запись выживает ровно на floor; sub-floor raw decay вытесняется, оставаясь required; retention 0.5. |
| `leakage_decoy` | Cross-scope decoy на чётных индексах | Decoy members дают `leakage_free = False` при ненарушенной attribution precision. |
| `cross_session_decoy_reuse` | Session-beta reuse реального vs decoy experience | Реальный experience reuse даёт recall 1.0; decoy reuse — experience-reuse recall 0.0. |

Expectation table пересобирается арифметически из generator metadata при каждом вычислении (`expected_metrics_v3`), поэтому generator и evaluator обязаны соглашаться независимо.

## Module contract

- `AdversarialCorpusCaseV3` — frozen dataclass с `payload()` (canonical JSON dict), `provenance_digest()` (`sha256:` над canonical payload) и проекциями `to_memory_quality_case()` / `to_trajectory_step()` в типы core evaluator.
- `_LcgRandom` портирует 32-bit LCG stream из `work_product_ma08_ma09` (high-bit draws избегают коротких циклов); minting идентификаторов гарантирует уникальность с bounded retries (`source_id_space_exhausted`, `lcg_draw_space_exhausted`, `lcg_bound_invalid` на некорректных границах).
- `generate_corpus_v3(seed, cases_per_category)` fail-closed валидирует параметры и перед возвратом гоняет внутренние probes: уникальные case ids (`duplicate_corpus_case_id`), точный размер (`corpus_size_invalid`), точный набор категорий (`corpus_category_set_invalid`), равенство replay того же seed (`same_seed_divergence_detected`), неравенство digests разных seeds (`cross_seed_collision_detected`) и дизъюнктность case ids разных seeds (`cross_seed_id_collision_detected`). Нарушенное свойство прерывает generation вместо эмита непроверяемого corpus.
- `project_decay_strengths_v3(base_strengths, periods)` применяет экспоненциальный decay с clamp на `Memory.DECAY_FLOOR` (0.1) из [`noesis_harness/memory.py`](../../../noesis_harness/memory.py), зеркаля decay-модель хранилища.
- `verify_case_provenance_v3(case)` пересобирает payload чисто из evaluator-bound полей через trajectory round-trip и сравнивает digest'ы.
- `_check_decay_boundary_v3(case)` fail-closed валидирует арифметику decay fixture (`decay_fixture_invalid`).
- `evaluate_corpus_v3(adapter_factory, seed, cases_per_category)` записывает все cases через adapter по sessions, оценивает через `MemoryQualityEvaluator` и возвращает отчёт: `schema_version` (`noesis.memory-quality-corpus.v3`), `per_case` (метрики плюс `provenance_verified`, `decay_floor_boundary_respected`, `expectation_violations`), aggregate metrics, `duplicate_attribution_inflation_detected`, `categories`, `corpus_digest`, `seed`, `session_ids`, встроенная строка `claim_boundary`, байт-стабильный `report_digest`.
- Adapter contract: фабрика обязана быть callable и вернуть объект с callable `record_trajectory(session_id, steps)` и `evaluate_sessions(sessions)`; нарушения поднимают `adapter_factory_invalid` / `adapter_contract_invalid`; неизвестные или отсутствующие expectation entries поднимают `expectation_key_unknown` / `expectation_entry_missing`.

## Typed values and error codes

Коды `MemoryQualityCorpusError`: `seed_invalid`, `cases_per_category_invalid`, `cases_per_category_out_of_range`, `lcg_bound_invalid`, `lcg_draw_space_exhausted`, `source_id_space_exhausted`, `duplicate_corpus_case_id`, `corpus_size_invalid`, `corpus_category_set_invalid`, `same_seed_divergence_detected`, `cross_seed_collision_detected`, `cross_seed_id_collision_detected`, `category_unknown`, `expectation_entry_missing`, `expectation_key_unknown`, `adapter_factory_invalid`, `adapter_contract_invalid`, `decay_fixture_invalid`.

Per-case булевы поля имеют закрытый словарь (`provenance_verified`, `decay_floor_boundary_respected`, `budget_respected`, `leakage_free`); метрики — float в [0, 1], кроме счётчиков токенов и целого `seed`.

## Wiring status

На 2026-08-25 [`scripts/run_memory_quality_evidence.py`](../../../scripts/run_memory_quality_evidence.py) вызывает `evaluate_corpus_v3` через `run_adversarial_corpus_v3()` и эмитит её отчёт аддитивно как верхнеуровневый ключ evidence `adversarial_corpus_v3` (schema evidence остаётся `noesis.memory-quality-evidence.v3`; отчёт corpus хранит свой `noesis.memory-quality-corpus.v3`). Регенерированный [`docs/MEMORY_QUALITY_EVIDENCE.json`](../../MEMORY_QUALITY_EVIDENCE.json) байт-стабилен между повторными запусками.

## Related tests

- [`tests/test_memory_quality_corpora_v3.py`](../../../tests/test_memory_quality_corpora_v3.py) — байтовое равенство same-seed включая digest'ы, расхождение id/content между seeds, покрытие size/category/id, полнота expectation table, fail-closed параметров, детекция temporal inversion динамически по категории, edges decay/leakage/budget/reuse, падающие видимо либо никак, детерминизм кастомного `cases_per_category`, fail-closed нарушений adapter contract.

## Provenance

Заимствованные паттерны: evalscope seeded-fixture generation (явная seeded-процедура над конечными таблицами, версонируемая schema, стабильные digest'ы, seed-sensitivity probes); decay-floor model agentmemory (затухание силы с clamp на floor); LCG stream портирован из `work_product_ma08_ma09`; fail-closed expectation checks в духе adversarial suites deepseek-harness; recorded-trajectory scoring следует линии quality-trace agentmemory из `scripts/run_memory_quality_evidence.py`.

## Claim boundary

Evidence только локальный и детерминированный: seeded generated константы, оцениваемые локальным stdlib evaluator'ом поверх реальных durable Memory operations, открытых adapter factory. Digest'ы report и corpus подтверждают воспроизводимость generation и scoring math на этой машине в данном pinned состоянии кода. Это не внешний model benchmark, не измерение качества production memory и не сравнение с другими агентами или harness'ами.
