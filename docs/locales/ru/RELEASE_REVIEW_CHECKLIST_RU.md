# NOESIS — чек-лист release review (подготовка Gate 8)

**Контрольная точка:** 2026-08-26, commit репозитория `127b28d`
**Нормативный источник:** абзац Gate 8 в [`PLAN_NOESIS_1.0_MASTER_RU.md`](PLAN_NOESIS_1.0_MASTER_RU.md) (English primary: [`../../RELEASE_REVIEW_CHECKLIST.md`](../../RELEASE_REVIEW_CHECKLIST.md))
**Runtime policy:** для release gates только Python 3.14; детерминированное ядро — stdlib-only.
**Модель эксплуатации:** local-first, private-by-default, human-governed, fail-closed.

## Назначение

Документ связывает все существующие release-значимые артефакты и верификаторы в одну упорядоченную операторскую процедуру. Он определяет, что запускать, какой вывод считается прохождением, каково зафиксированное состояние этого хоста и что нельзя заявлять при отказе этапа. Это процедура, а не доказательство: её выполнение не создаёт claims о возможностях, parity или превосходстве сверх артефактов, которые она проверяет.

## Как читать документ

| Соглашение | Значение |
|---|---|
| Exit code | `0` = этап пройден; `2` = отказ, blocked или fail-closed отказ выполнить. |
| Status vocabulary | `passed`, `not_run`, `blocked`, `unsupported`. Непройденные статусы никогда не конвертируются в успех. |
| Ключ подписи | `NOESIS_EXTERNAL_EVIDENCE_KEY` (минимум 16 байт) — операторский, не коммитится, требуется всем HMAC-верификаторам. |
| Интерпретатор | Этапы release gate выполняются под `py -3.14`; shell-дефолтный `python` на этом хосте — 3.11.9 и проваливает runtime gate by design. |
| Текущий статус | Честное зафиксированное состояние хоста на checkpoint commit. Оно описательное, не желаемое, и обновляется при изменении evidence. |

Этапы выполняются по порядку. Отказавший этап либо прерывает review (см. Hard stop conditions), либо ограничивает итог внутренним статусом internal-release-candidate. Пропуск этапа с последующим описанием как «покрытого» запрещён.

## Обзор этапов

| # | Этап | Опорные артефакты |
|---|---|---|
| 1 | Runtime gate | идентичность Python 3.14 |
| 2 | Локальные suites | unittest discovery, documentation audit tests |
| 3 | Benchmarks | фиксированные recall/workload gates |
| 4 | Регенерация evidence | [`../../MEMORY_QUALITY_EVIDENCE.json`](../../MEMORY_QUALITY_EVIDENCE.json), [`../../MULTI_AGENT_WORKLOAD_EVIDENCE.json`](../../MULTI_AGENT_WORKLOAD_EVIDENCE.json) |
| 5 | Состояние external lanes (Gate 7) | [`../../PINNED_LANE_MATRIX_314.json`](../../PINNED_LANE_MATRIX_314.json), [`../../MODEL_TASK_3LANE_BLOCKERS.json`](../../MODEL_TASK_3LANE_BLOCKERS.json), [`../../COMPARATIVE_BASELINE_VERSION_SMOKE.json`](../../COMPARATIVE_BASELINE_VERSION_SMOKE.json) |
| 6 | Состояние native-артефакта (Gate 6) | [`../../NATIVE_WINDOWS_ARTIFACT_EVIDENCE.json`](../../NATIVE_WINDOWS_ARTIFACT_EVIDENCE.json), [`../../CROSS_PLATFORM_RELEASE_GATE_MATRIX.json`](../../CROSS_PLATFORM_RELEASE_GATE_MATRIX.json) |
| 7 | Signed evidence pipeline | bundle `reports/evidence-pipeline/` плюс offline-верификаторы ([`../../OPERATOR_EVIDENCE_PIPELINE.md`](../../OPERATOR_EVIDENCE_PIPELINE.md)) |
| 8 | Transfer audit | post-transfer audit скопированной директории ([`../../POST_TRANSFER_AUDIT.md`](../../POST_TRANSFER_AUDIT.md)) |
| 9 | Аудиты ссылок и docs | markdown links, JSON evidence parseability, docs security |
| 10 | Human review items | лицензии/provenance, границы README, локализация |

## Этап 1 — Runtime gate

```powershell
py -3.14 scripts\verify_python314.py --json
```

Ожидание: exit `0`, `"ok": true`, `"required": "3.14.x"`.

Текущий статус на этом хосте: `py -3.14` установлен, коммитнутые артефакты фиксируют `3.14.7` ([`../../../reports/evidence-pipeline/release-readiness.json`](../../../reports/evidence-pipeline/release-readiness.json)). Shell-дефолтный `python` — `3.11.9`; запуск gate под ним возвращает exit `2`, что является корректным поведением, а не дефектом инструмента.

При отказе этапа: нельзя заявлять «full Python 3.14 validation», все последующие этапы теряют runtime-основание. Перезапуск под 3.11 этот gate не закрывает.

## Этап 2 — Локальные test suites

```powershell
py -3.14 -m unittest discover -s tests -q
py -3.14 -m unittest tests.test_documentation_audit -q
```

Ожидание: exit `0`, без failures и errors.

Текущий статус на этом хосте: последняя зафиксированная полная валидация в signed snapshot — `validated_test_count: 1057` под Python `3.14.7` ([`../../../reports/evidence-pipeline/release-readiness.json`](../../../reports/evidence-pipeline/release-readiness.json)). При составлении чек-листа suite повторно не запускался; AGENTS.md требует его зелёным при каждом изменении. Bounded recovery discovery runner дополнительно фиксирует `91/91 passed` на Windows lane в [`../../RECOVERY_DISCOVERY_EVIDENCE.json`](../../RECOVERY_DISCOVERY_EVIDENCE.json); таймаут там классифицируется как `incomplete`, никогда как успех.

При отказе: нельзя заявлять regression-free release candidate, а snapshot, регенерированный на этапе 7, нёс бы устаревшее или ложное число тестов.

## Этап 3 — Детерминированные benchmarks

```powershell
py -3.14 benchmarks\recall20.py
py -3.14 benchmarks\workload20.py
```

Ожидание: exit `0` у обоих. `recall20` требует точность не ниже `0.80` на фиксированном fixture из 20 запросов; `workload20` складывает фиксированный rubric evaluator с одним bounded multi-lane replay.

Текущий статус на этом хосте: детерминированные фикстуры без сети и wall-clock входов. Коммитнутые parallel audit lanes фиксируют workload digest `sha256:03292a7c...76909` как `passed` в [`../../PARALLEL_RELEASE_AUDIT_EVIDENCE.json`](../../PARALLEL_RELEASE_AUDIT_EVIDENCE.json). При составлении не перезапускались.

При отказе: нельзя заявлять local benchmark-parity (см. [`../../P13_LOCAL_BENCHMARK_PARITY_PY314_EVIDENCE.json`](../../P13_LOCAL_BENCHMARK_PARITY_PY314_EVIDENCE.json)); формулировки про deterministic evidence убираются из release notes до зелёного результата.

## Этап 4 — Регенерация evidence и byte stability

Регенерировать два детерминированных документа и требовать побайтового совпадения:

```sh
make evidence-local
git diff --exit-code -- docs/MEMORY_QUALITY_EVIDENCE.json docs/MULTI_AGENT_WORKLOAD_EVIDENCE.json
```

Make-цель разворачивается в `python -m scripts.run_memory_quality_evidence > docs/MEMORY_QUALITY_EVIDENCE.json` и `python -m scripts.run_workload_evidence --output docs/MULTI_AGENT_WORKLOAD_EVIDENCE.json`. На Windows воспроизводите редирект байт-точно (POSIX shell или `PYTHONUTF8=1`); PowerShell 5.1 `>` переписывает кодировку и создаёт ложный drift.

Опциональный honest-host sandbox report (только stdout, никогда не трактуется как native parity):

```powershell
py -3.14 -m scripts.run_sandbox_conformance
```

Ожидание: регенерация даёт нулевой diff; conformance печатает схему `noesis.sandbox-conformance.v2` с явными непройденными записями для недоступных native путей исполнения.

Текущий статус на этом хосте: оба коммитнутых документа byte-stable by construction (нет wall-clock полей); записи conformance Windows backend остаются на уровне command inspection согласно [`../../NATIVE_EVIDENCE_HONESTY_GATE.md`](../../NATIVE_EVIDENCE_HONESTY_GATE.md).

При отказе (ненулевой diff): коммитнутый evidence не соответствует коду. Review останавливается до регенерации и коммита артефакта либо отката изменения кода. Claim «deterministic evidence» drift не переживает.

## Этап 5 — Состояние external lanes (Gate 7)

Команды оператора по re-pin и планированию. Они перезаписывают коммитнутые planning-артефакты; при подготовке чек-листа не выполнялись:

```sh
python scripts/pin_external_revisions.py --output docs/PINNED_EXTERNAL_MANIFEST_DRAFT.json
python scripts/pinned_lane_orchestrator.py \
  --manifest docs/PINNED_EXTERNAL_MANIFEST_DRAFT.json \
  --workspace _temp/pinned-ws \
  --output docs/PINNED_LANE_MATRIX_314.json
```

Фактический запуск lane остаётся отдельной операторской pinned-runner операцией с approval-квитанциями `noesis.external-approval.v1` (см. [`../../PINNED_LANE_OPERATOR_PREFLIGHT.md`](../../PINNED_LANE_OPERATOR_PREFLIGHT.md)). Подписанные receipts после получения загружаются офлайн через `scripts/aggregate_external_evidence.py` без запуска чего-либо.

Зафиксированное состояние (читать, без нужды не регенерировать):

| Артефакт | Зафиксированный статус |
|---|---|
| [`../../PINNED_LANE_MATRIX_314.json`](../../PINNED_LANE_MATRIX_314.json) | readiness `overall_status: blocked`, `comparative_ready: false`; deepseek_harness `not_run` (unavailable, revision pinned), hermes `not_run` (missing exact revision), opencode ready for operator approval, исполнение `not_started` |
| [`../../MODEL_TASK_3LANE_BLOCKERS.json`](../../MODEL_TASK_3LANE_BLOCKERS.json) | opencode `passed` с `task_success: 1.0`; hermes `blocked` (бинарник карантирован антивирусом; отсутствует `OPENAI_API_KEY`); deepseek_harness `blocked` (отсутствует DSH profile stack; отсутствует `DEEPSEEK_API_KEY`). Пути разблокировки перечислены per lane в артефакте |
| [`../../EXTERNAL_EVIDENCE_READINESS_MATRIX.json`](../../EXTERNAL_EVIDENCE_READINESS_MATRIX.json) | `overall_status: not_run`, `comparative_ready: false` |
| [`../../COMPARATIVE_BASELINE_VERSION_SMOKE.json`](../../COMPARATIVE_BASELINE_VERSION_SMOKE.json) | signed aggregate `overall_status: passed` с `execution_claim: evidence_ingestion_only` |

Baseline smoke aggregate доказывает только то, что три подписанные квитанции приняты ingestion-контрактом. Он не доказывает, что какая-либо external lane в момент агрегации произвела результат задачи.

Если состояние отличается от «все required lanes `passed` с одним protocol fingerprint»: нельзя заявлять comparative ranking, преимущество A/B или external-execution claim. Gate 7 остаётся открытым.

## Этап 6 — Состояние native-артефакта (Gate 6)

Офлайн metadata-верификация локального development-артефакта:

```powershell
py -3.14 scripts\verify_native_artifact.py --target windows --artifact dist\noesis-harness.exe --development-unsigned --output _temp\native-windows-evidence.json
```

Ожидание: exit `0` означает, что shape, host binding и SHA-256 внутренне согласованы для явно неподписанного development-артефакта. Это не заявление о подписи и не parity statement.

Зафиксированное состояние на этом хосте ([`../../NATIVE_WINDOWS_ARTIFACT_EVIDENCE.json`](../../NATIVE_WINDOWS_ARTIFACT_EVIDENCE.json)):

| Поле | Значение |
|---|---|
| `evidence_status` | `development_unsigned` |
| `signature.status` | `not_run` (`signtool` присутствует, сертификат недоступен) |
| SHA-256 | `558ddfe906a5bb1ad98686597d5927a3944191ac03c29e667af57527a4579a48` |
| host | windows, AMD64, Python 3.14.7, `platform_ok` и `python_ok` true |
| macOS lane | `not_run` (нет matching host) |

Native parity bundles ([`../../NATIVE_PARITY_OPERATOR_RUNBOOK.md`](../../NATIVE_PARITY_OPERATOR_RUNBOOK.md): `scripts/run_native_parity.ps1`, `scripts/run_native_parity_macos.sh`) в machine-readable matrix остаются неисполненными; Windows-хост существует, но ни один запуск bundle не прошёл валидацию `scripts/validate_native_parity.py`.

Заявлять больше зафиксированного запрещено: никаких signed/notarized artifact claim, никаких native Windows/macOS parity claim и никакой формулировки «production binary», пока `signature.status` равен `not_run`, а строки parity matrix равны `not_run`.

## Этап 7 — Signed evidence pipeline (регенерация плюс офлайн-верификация)

Каноническая bounded-регенерация (пишет `reports/evidence-pipeline/`; возвращает `2`, пока lanes непройдены, — это документированное правило распространения статуса):

```sh
python scripts/run_operator_evidence_pipeline.py \
  --manifest benchmarks/external_ab_manifest_v1.json \
  --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" \
  --output-dir reports/evidence-pipeline \
  --readiness-test-count 1057 \
  --readiness-python-version 3.14.7 \
  --native-status not_run \
  --external-status not_run
```

Офлайн-верификаторы против коммитнутого bundle:

```sh
python scripts/verify_release_readiness.py --snapshot reports/evidence-pipeline/release-readiness.json
python scripts/verify_release_gate_artifact.py --artifact reports/evidence-pipeline/release-gate.json
python scripts/verify_reproducibility_receipt.py --root reports/evidence-pipeline --key "$NOESIS_EXTERNAL_EVIDENCE_KEY"
python scripts/verify_operator_artifact_set.py --root reports/evidence-pipeline --key "$NOESIS_EXTERNAL_EVIDENCE_KEY"
./scripts/post_transfer_audit.sh --root reports/evidence-pipeline --key "$NOESIS_EXTERNAL_EVIDENCE_KEY"
./scripts/release_gate.sh --root reports/evidence-pipeline --key "$NOESIS_EXTERNAL_EVIDENCE_KEY" --snapshot reports/evidence-pipeline/release-readiness.json
```

Ожидаемые текущие результаты и их причины:

| Верификатор | Ожидание сегодня | Причина |
|---|---|---|
| `verify_release_readiness.py` | exit `0` | Snapshot внутренне согласован; честно фиксирует `overall_status: blocked` с blockers `matching_native_windows_macos_hosts_required`, `pinned_external_lane_receipts_required` |
| `verify_release_gate_artifact.py` | exit `0` | Digest и claim boundary артефакта валидны; записанный `gate_status` остаётся `not_run` |
| `verify_reproducibility_receipt.py` | exit `0` с оригинальным ключом; иначе `2` | Цепочка digest связывается только ключом оператора, которым подписана |
| `verify_operator_artifact_set.py` (strict wrapper) | exit `2` | Readiness matrix равна `not_run`, поэтому требование полной цепочки корректно отказывает |
| `post_transfer_audit.sh` | exit `2`, `failed_stage: artifact_chain` | Та же fail-closed причина; composition и reproducibility стадии исправны |
| `release_gate.sh` | exit `2` | Первая стадия наследует blocked chain |

Эти отказы — зафиксированный разрыв Gate 6/7, а не неисправность верификаторов. Они ограничивают review статусом internal-release-candidate. См. [`../../RELEASE_READINESS_VERIFIER.md`](../../RELEASE_READINESS_VERIFIER.md), [`../../REPRODUCIBILITY_VERIFIER.md`](../../REPRODUCIBILITY_VERIFIER.md), [`../../OFFLINE_OPERATOR_ARTIFACT_VERIFIER.md`](../../OFFLINE_OPERATOR_ARTIFACT_VERIFIER.md) и [`../../RELEASE_GATE.md`](../../RELEASE_GATE.md).

Если какой-либо верификатор сообщает о tampering, digest mismatch или schema violation вместо честного status-driven block: это hard stop condition ниже, а не ожидаемое поведение.

## Этап 8 — Transfer audit

Скопируйте `reports/evidence-pipeline/` на принимающий хост или носитель и проверьте копию без регенерации:

```powershell
.\scripts\post_transfer_audit.ps1 `
  --root <copied-dir> `
  --key $env:NOESIS_EXTERNAL_EVIDENCE_KEY
.\scripts\verify_operator_artifacts.ps1 --root <copied-dir> --key $env:NOESIS_EXTERNAL_EVIDENCE_KEY
```

Ожидание: те же результаты, что на этапе 7, при том же ключе. Успешное копирование не меняет ни одного статуса; transfer доказывает только целостность composition и digest ([`../../PORTABLE_TRANSFER_AUDIT.md`](../../PORTABLE_TRANSFER_AUDIT.md)). Неожиданные лишние файлы в директории fail-closed ломают composition by design.

Отказ на нетронутой копии с оригинальным ключом: hard stop. Разобраться до любого дальнейшего распространения.

## Этап 9 — Аудиты ссылок и docs

```sh
python scripts/check_markdown_links.py --root .
python scripts/check_json_evidence.py --root .
python scripts/docs_security_audit.py --root .
```

Ожидание: exit `0` у всех трёх (`clean: true`, `CLEAN`). Дополнительно `py -3.14 -m unittest tests.test_documentation_audit -q` должен проходить (покрыто этапом 2).

Аудит локализации: каждый English-primary release-документ имеет русский supplemental mirror в `locales/ru/` с командами дословно. Зеркало этого документа — `RELEASE_REVIEW_CHECKLIST_RU.md`; нормативное зеркало плана — [`PLAN_NOESIS_1.0_MASTER_RU.md`](PLAN_NOESIS_1.0_MASTER_RU.md).

Текущий статус на этом хосте: link и docs-security аудиты чистые на момент составления; пара локализации создана вместе с этим документом.

При отказе любого аудита: битые ссылки, нечитаемый evidence JSON или небезопасные copy/paste примеры блокируют documentation release. Чинятся источники, а не ослабляются аудиторы.

## Этап 10 — Human review items

Не исполняется автоматически; каждый пункт требует именованного reviewer и записанного решения.

| Пункт | Исходные материалы |
|---|---|
| Лицензии и third-party attribution obligations | [`../../../THIRD_PARTY_NOTICES.md`](../../../THIRD_PARTY_NOTICES.md), [`../../third_party_provenance.json`](../../third_party_provenance.json), provenance discipline в [`../../../RESEARCH_DAIGEST.md`](../../../RESEARCH_DAIGEST.md) |
| README декларирует verified capabilities и unresolved boundaries | `README.md` репозитория; honesty criterion в [`PLAN_NOESIS_1.0_MASTER_RU.md`](PLAN_NOESIS_1.0_MASTER_RU.md) |
| Claim progress matrix согласуется с артефактами | [`../../CLAIMS_PROGRESS_MATRIX.json`](../../CLAIMS_PROGRESS_MATRIX.json), roadmap reconciliation guard [`../../ROADMAP_RECONCILIATION_EVIDENCE.json`](../../ROADMAP_RECONCILIATION_EVIDENCE.json) |
| Полнота локализации изменённых docs | зеркала в `locales/ru/` |
| Актуальность changelog и release metadata | `CHANGELOG.md`, packaging metadata |
| Никаких формулировок сверх зафиксированного evidence | reviewer сверяет каждое публичное предложение с артефактами этапов 4-8 |

Human review может отклонить релиз даже при прохождении всех исполняемых этапов. Он никогда не одобряет формулировки, которые артефакты не поддерживают.

## Hard stop conditions

Release review немедленно прерывается, и никакого частичного зачёта не остаётся, при любом из условий:

1. Этап 1 провален: активный интерпретатор не Python 3.14.
2. Любой unit test, benchmark или documentation-audit test падает (этапы 2, 3, 9).
3. Регенерация детерминированного evidence расходится с коммитнутыми байтами (этап 4).
4. Любой верификатор сообщает tampering, ошибку подписи, digest mismatch, schema violation или неожиданный transfer composition (этапы 7, 8) — в отличие от честного непройденного статуса.
5. `native_or_external_execution_claim` равен `true` где угодно, либо любой lane со статусом `not_run`/`blocked` подаётся как пройденный в тексте или артефактах.
6. `scripts/release_audit.py` завершается с `2` по причинам помимо ожидаемого blocked external matrix: secret-like hits, использование `eval`/`exec`, syntax errors, грязное рабочее дерево, несогласованность roadmap или ошибки readiness-артефакта.
7. Валидатор parallel release audit отклоняет свежий отчёт (включая `working_tree_clean` false после коммита правок review).
8. Подписанные receipts отсутствуют там, где строгая цепочка их требует, либо ключ оператора не воспроизводит записанные digest.
9. Пункт human review не закрыт либо reviewer зафиксировал несогласие с claim boundary.

Известные текущие блокеры под эти условия на этом хосте: грязное рабочее дерево (два изменённых docs, два untracked appcontainer файла), внешняя readiness `not_run`, native signature `not_run`. Пока каждый не закрыт, единственный допустимый исход review — внутренний release candidate с явно указанными границами.

## Приложение: clean-tree release audit

После коммита всех правок review выполните read-only аудит и parallel lanes:

```sh
python scripts/release_audit.py --root .
python scripts/run_parallel_release_audit_lanes.py --output docs/PARALLEL_RELEASE_AUDIT_EVIDENCE.json
python scripts/validate_parallel_release_audit_report.py docs/PARALLEL_RELEASE_AUDIT_EVIDENCE.json
```

Ожидание: exit `0` у всех трёх; валидатор требует пять пройденных lanes, чистое рабочее дерево, ноль секретов и digest-корректный workload evidence ([`../../RELEASE_AUDIT_EXTERNAL_READINESS.md`](../../RELEASE_AUDIT_EXTERNAL_READINESS.md)). Вариант с опциональным `--remote --remote-branch <branch>` добавляет opt-in remote SHA parity; без него сетевых операций нет.

## Claim boundary

Этот чек-лист процедурен. Его выполнение, полное или частичное, не создаёт claim о superiority, native Windows/macOS parity или external execution сверх того, что по отдельности фиксируют упомянутые signed-артефакты. Статусы `not_run` и `blocked` остаются именно ими независимо от числа пройденных этапов. Критерий честности, включая условие, при котором гипотеза мирового первенства могла бы стать проверяемой, определяется исключительно [`PLAN_NOESIS_1.0_MASTER_RU.md`](PLAN_NOESIS_1.0_MASTER_RU.md) и его English primary источником [`../../RELEASE_REVIEW_CHECKLIST.md`](../../RELEASE_REVIEW_CHECKLIST.md) с нормативным планом [`PLAN_NOESIS_1.0_MASTER.md`](../../PLAN_NOESIS_1.0_MASTER.md).
