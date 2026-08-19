# Operator Import Validation

` scripts/validate_operator_import.py` проверяет readiness-only operator bundle перед импортом signed lane и case evidence. Он не запускает providers, не потребляет approvals и не превращает `not_run` в результат.

Validator пересчитывает bundle digest, связывает bundle с exact manifest digest и case IDs, проверяет required lane set, revision/protocol drift и передаёт signed evidence и case validation в comparative report builder. Любой bundle, manifest или lane drift даёт `status=blocked` и не создаёт score.

| Import status | Значение |
|---|---|
| `blocked` | Bundle или evidence identity inconsistent, tampered, unsafe или malformed. |
| `accepted_not_run` | Bundle согласован, но external evidence неполный или lanes остаются `not_run`. |
| `accepted` | Signed evidence и полный case corpus приняты report builder. Это всё ещё не устанавливает `score_claim=true`. |

Output всегда содержит `external_execution_claim=false` и `score_claim=false`. Валидный import означает ingestion evidence, а не claim сравнительного превосходства. Provider execution находится за пределами этой команды и требует отдельного explicit operator action на matching pinned environment.

*Supplemental language: Russian.*
