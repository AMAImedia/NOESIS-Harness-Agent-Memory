# Статус релизного обзора NOESIS — 2026-08-27

**Документ:** фиксирует выполнение этапов из [`RELEASE_REVIEW_CHECKLIST.md`](RELEASE_REVIEW_CHECKLIST.md) на данном хосте. Этот пересмотр охватывает этапы 5-10, а также повторный прогон тестовой suites и аудит релиза на чистом дереве (шаг верификации).
**Коммит хоста:** `9f6a816` (рабочее дерево восстановлено до закоммиченного состояния после прогона тестов в этой сессии; см. Новые находки).
**Назначение:** запись статуса, не доказательство возможностей. Перечисляет что было запущено, что прошло и что остаётся заблокированным.
**Интерпретатор:** `py -3.14` (CPython 3.14.7). Интерпретатор по умолчанию `python` — это 3.11.9 и по замыслу не проходит runtime-гейт.

## Результаты этапов

| # | Этап | Результат | Примечания |
|---|---|---|---|
| 1 | Runtime-гейт | PASSED (перенесено) | 3.14.7; в этой сессии не перезапускался, интерпретатор неизменен |
| 2 | Локальные suites | FAIL (повторный прогон) | `py -3.14 -m unittest discover -s tests -q` -> 1152 теста, 1 падение, 18 пропущено. Прежнее «1110 OK» заменено. См. Новые находки про загрязнение самогенерирующимся тестом |
| 3 | Бенчмарки | PASSED (зафиксировано) | recall20 acc=1.00, workload20 score=0.8083; в этой сессии не перезапускались |
| 4 | Регенерация доказательств | RESOLVED (зафиксировано) | закоммиченные доказательства байт-стабильны; в этой сессии не перезапускалось |
| 5 | Состояние внешних лейн (Gate 7) | PARTIAL | Read-only инспекция закоммиченных артефактов (ниже). Внешнее выполнение не производилось; нет comparative/A-B утверждения |
| 6 | Нативный артефакт | PARTIAL (повторно верифицировано) | `verify_native_artifact.py` exit 0, `evidence_status: development_unsigned`; подпись `not_run` (signtool присутствует, сертификат недоступен); macOS-лейн `not_run` (нет подходящего хоста) |
| 7 | Подписанный конвейер доказательств | NOT RUN / BLOCKED | `verify_release_readiness.py` exit 0 (status passed, фиксирует `overall_status: blocked`); `verify_release_gate_artifact.py` exit 0 (`gate_status: not_run`); `verify_reproducibility_receipt.py` BLOCKED exit 2 (`--key` обязателен, `NOESIS_EXTERNAL_EVIDENCE_KEY` не задан); `verify_operator_artifact_set.py` BLOCKED exit 2 (аналогично) |
| 8 | Аудит передачи | NOT RUN / BLOCKED | Передача не производилась (read-only задача, нет внешнего носителя). `post_transfer_audit` требует `--key` (не задан). Та же fail-closed причина, что у этапа 7 |
| 9 | Аудит ссылок и документации | PASSED | `check_markdown_links.py` exit 0 (445 ссылок, 0 отсутствующих); `check_json_evidence.py` exit 0 (clean/parseable); `docs_security_audit.py` exit 0 (CLEAN) |
| 10 | Ручной обзор | PENDING | Не исполняемо; требует именованного ревьюера и зафиксированных решений |

### Состояние артефактов этапа 5 (read-only, подтверждено в этой сессии)

| Артефакт | Зафиксированный статус |
|---|---|
| `docs/PINNED_LANE_MATRIX_314.json` | все лейны `not_run` (deepseek_harness, hermes, opencode) |
| `docs/MODEL_TASK_3LANE_BLOCKERS.json` | присутствует; записи блокеров по лейнам целы (успех opencode заблокирован ключом; hermes/deepseek нужны бинарники+ключи) |
| `docs/COMPARATIVE_BASELINE_VERSION_SMOKE.json` | `overall_status: passed`, `comparative_ready: true`, `execution_claim: evidence_ingestion_only` (только ингестция, без выполнения лейна) |
| `docs/EXTERNAL_EVIDENCE_READINESS_MATRIX.json` | `overall_status: not_run`, `comparative_ready: false` |

Gate 7 остаётся открытым. Baseline version-smoke доказывает лишь то, что подписанные receipt были приняты контрактом ингестции; он не доказывает, что какой-либо внешний лейн выдал результат задачи.

## Наблюдаемые условия жёсткой остановки

| Условие | Статус |
|---|---|
| 1. Не Python 3.14 | CLEAR (3.14.7) |
| 2. Падение теста/бенчмарка/док-аудита | FAIL — полная suite 1 падение (`test_bridge_discovery` hermes, только в полном прогоне; см. Новые находки). Аудиты ссылок/json/безопасности документации чисты |
| 3. Дрейф доказательств | CLEAR (в этой сессии регенерации не было; закоммиченные доказательства неизменны) |
| 4. Подтасовка верификатором | CLEAR (блоки этапа 7 статус-зависимы / зависят от ключа; нет подтасовки, несовпадения дайджеста или нарушения схемы) |
| 5. `native_or_external_execution_claim` true | CLEAR (false по всем артефактам) |
| 6. `release_audit.py` exit 2 вне заблокированной матрицы | CLEAR — на чистом дереве exit 0, `clean: true`, `working_tree_clean: true`, `secret_like_hits: []` (только `synthetic_fixture_hits` в `security_holdouts.py`, классифицирован как synthetic fixture) |
| 7. Валидатор параллельного аудита релиза отвергает | NOT RUN в этой сессии (appendix `run_parallel_release_audit_lanes.py` не запускался); статус неизвестен, не заявляется |
| 8. Отсутствуют подписанные receipt | ACTIVE — внешние лейны model_task требуют операторских ключей (`DEEPSEEK_API_KEY`/`OPENAI_API_KEY` отсутствуют; `NOESIS_EXTERNAL_EVIDENCE_KEY` не задан) |

## Новые находки (этой сессии)

1. **Загрязнение полной suite тестом (корневая причина падения этапа 2).** Запуск `py -3.14 -m unittest discover -s tests -q` как предписано гейтом имел побочный эффект: самобутстрапящийся тест сгенерировал `noesis_harness/self_audit.py` и `tests/test_self_audit.py` (оба untracked) и изменил `noesis_harness/__init__.py` (добавил блок импорта `self_audit`). Это (а) загрязнило рабочее дерево, (б) увеличило обнаруженное число тестов с зафиксированных 1110 до 1152, и (в) загрязнило глобальное состояние модулей, из-за чего `test_bridge_discovery.BridgeDiscoveryTests.test_ready_hermes_capability_and_matching_model` возвращает `unavailable` в полном прогоне, хотя проходит изолированно. Это дефект гигиены тестов (нарушает дисциплину чистого дерева и запрета мутаций), а не сбой от внешней зависимости. Закоммиченное дерево восстановлено: откачен `noesis_harness/__init__.py` и перемещены два сгенерированных файла в `_archive/noesis_harness_self_audit_2026-08-27.py` и `_archive/tests_test_self_audit_2026-08-27.py`. Дефект должен быть исправлен до того, как этап 2 можно будет считать зелёным.

2. **Примечание к импортам `release_audit.py` для верификаторов этапа 7.** `verify_release_readiness.py` / `verify_release_gate_artifact.py` / `verify_reproducibility_receipt.py` / `verify_operator_artifact_set.py` используют импорты `from scripts...` и требуют корень репо в `PYTHONPATH` (голый `python scripts/x.py` падает с `ModuleNotFoundError: No module named 'scripts'`). Запускать как `PYTHONPATH=. py -3.14 scripts/<verifier> ...`. С этим readiness и gate-artifact выходят 0 как в документации; reproducibility и artifact-set выходят 2 исключительно потому, что обязателен `--key`, а `NOESIS_EXTERNAL_EVIDENCE_KEY` не задан.

### Пути доказательств, произведённых в этой сессии

- `_temp/native-windows-evidence.json` — вывод `verify_native_artifact.py` этапа 6 (`evidence_status: development_unsigned`).
- `_temp/unittest.out`, `_temp/unittest.err` — захваченный полный прогон (1152 теста, 1 падение, 18 пропущено).
- `_temp` внесён в gitignore; не коммитится.

## Команды повторной верификации (фактические выводы)

```
py -3.14 -m unittest discover -s tests -q
  -> Ran 1152 tests in 214.092s
  -> FAILED (failures=1, skipped=18)
  -> failure: test_bridge_discovery.BridgeDiscoveryTests.test_ready_hermes_capability_and_matching_model
     AssertionError: 'unavailable' != 'ready'   (проходит изолированно)

py -3.14 scripts/release_audit.py --root .        # чистое дерево
  -> exit 0; clean: true; working_tree_clean: true; secret_like_hits: []
  -> synthetic_fixture_hits: [noesis_harness/security_holdouts.py private-key pattern]
  -> external_readiness.overall_status: not_run

py -3.14 scripts/check_markdown_links.py --root .
  -> exit 0; clean: true; local_links: 445; missing_count: 0

py -3.14 scripts/check_json_evidence.py --root .
  -> exit 0; clean: true

py -3.14 scripts/docs_security_audit.py --root .
  -> CLEAN (exit 0)

py -3.14 scripts/verify_native_artifact.py --target windows --artifact dist\noesis-harness.exe --development-unsigned --output _temp\native-windows-evidence.json
  -> exit 0; evidence_status: development_unsigned

PYTHONPATH=. py -3.14 scripts/verify_release_readiness.py --snapshot reports/evidence-pipeline/release-readiness.json
  -> exit 0; status: passed; overall_status: blocked

PYTHONPATH=. py -3.14 scripts/verify_release_gate_artifact.py --artifact reports/evidence-pipeline/release-gate.json
  -> exit 0; gate_status: not_run; status: passed

PYTHONPATH=. py -3.14 scripts/verify_reproducibility_receipt.py --root reports/evidence-pipeline
  -> exit 2; argparse: --key is required (NOESIS_EXTERNAL_EVIDENCE_KEY не задан) -> BLOCKED

PYTHONPATH=. py -3.14 scripts/verify_operator_artifact_set.py --root reports/evidence-pipeline
  -> exit 2; argparse: --key is required -> BLOCKED
```

## Итоговый статус

Проект остаётся **кандидатом внутреннего релиза**. Локальные гейты 1, 3, 4, 9 верифицированы/перенесены; нативный dev-unsigned артефакт этапа 6 повторно верифицирован; baseline version-smoke этапа 7 — `passed` (evidence_ingestion_only). Публично-заявляемый релиз остаётся заблокированным по:
1. Падение тестовой suite этапа 2 (1 падение, только в полном прогоне; вызвано самогенерирующим тестом, пишущим исходники) — должно быть исправлено до любого утверждения об отсутствии регрессий.
2. Внешние лейны `model_task` для hermes/deepseek (операторские API-ключи/кредиты; `NOESIS_EXTERNAL_EVIDENCE_KEY` не задан для подписанного конвейера).
3. Нативная подпись сертификатом от CA (релизного уровня); хост macOS для паритета.
4. Подпись ручного обзора по формулировкам границ утверждений.

## Граница утверждений

Эта запись статуса не создаёт утверждений о превосходстве по производительности, нативном паритете или внешнем выполнении. Все лейны `not_run`/`blocked` остаются ровно такими. Единственно допустимый исход — кандидат внутреннего релиза с явно stated границами.
