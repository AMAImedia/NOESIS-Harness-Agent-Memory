# Phase 6 — External Evidence Protocol

**Статус:** подготовлен локально, внешний запуск ещё не выполнен  
**Runtime локальной проверки:** CPython 3.14.7 Linux  
**Manifest:** `benchmarks/external_ab_manifest_v1.json`

## Архитектурная граница

NOESIS является самостоятельной программой. Hermes и OpenCode не входят в core, не являются обязательными runtime-зависимостями и не поставляют NOESIS память, безопасность или execution semantics. Возможные adapters являются только capability-aware внешней границей.

Для Phase 6 Hermes и OpenCode используются как **black-box baseline systems** в отдельных pinned environments. Цель запуска — не импортировать их код, а выдать сопоставимый task manifest и собрать воспроизводимые evidence records.

## Обязательный A/B protocol

| Элемент | Правило |
|---|---|
| Systems | `noesis`, `hermes`, `opencode` |
| Revision | Exact commit/version обязателен для каждого run |
| Model/provider | Одинаковая pinned модель для coding lane; provider фиксируется manifest |
| Generation | `temperature=0`, `max_output_tokens=4096` |
| Budgets | 300 s wall time, 20 agent steps, 32k context tokens, 64 KiB tool output |
| Network | Deny by default |
| Workspace | Disposable, seed SHA-256 обязателен, outside access denied |
| Credentials | Не передаются в disposable lane |
| Metrics | Success, patch correctness, tests, latency, budget, egress, credentials, approval bypass, workspace escape, recovery, human review |
| Missing evidence | `not_run` остаётся `not_run`; unsupported не превращается в zero failure |

## Что реально проверено локально

| Проверка | Результат |
|---|---|
| External runner contract tests | **7/7 passed** |
| Shell-safe argv and disposable workspace validation | Passed; `shell=False`, approval required |
| Dry-run lane | Не запускает process |
| Unapproved execution | Denied и записывает `not_run` |
| Approved controlled execution | Structured outcome passed |
| Synthetic evaluator | NOESIS local contract lane: 10/10 cases, test pass rate 1.0 |
| Hermes external execution | `not_run` |
| OpenCode external execution | `not_run` |
| Comparable ranking | **Запрещён**, потому что pinned external revisions/runners отсутствуют |

Synthetic report является plumbing verification и не является A/B quality result. Он подтверждает, что manifest, runner contract, explicit approval и `not_run` semantics работают.

## Следующий внешний gate

Оператор должен подготовить отдельные disposable environments для Hermes и OpenCode, зафиксировать exact revisions, same-model/provider policy, workspace seed digests и runner commands. После этого `scripts/run_external_lane.py` запускается отдельно для каждой системы только с `--execute --approve`. Полученные raw outputs проходят redaction, schema validation и signed-evidence ingestion. Только после успешной проверки всех трёх систем разрешается строить comparative report.

До этого момента корректная формулировка статуса: **NOESIS имеет подготовленный воспроизводимый внешний benchmark protocol и локально проверенный runner plumbing; external superiority не доказано**.
