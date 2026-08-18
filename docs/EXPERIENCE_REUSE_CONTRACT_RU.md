# Durable Experience Reuse Contract

`experience_reuse.py` добавляет read-only selector для повторного использования проверенного опыта между задачами. Его задача — не имитировать «большую память», а прозрачно выбирать ограниченный набор provenance-bearing records под тем же control-plane budget.

| Gate | Acceptance criterion |
|---|---|
| Provenance | Каждый reusable record обязан иметь `sha256:` provenance digest длиной 64 hex |
| Scope | Cross-agent или другой scope не проходит без явного `allowed_scopes` |
| Sensitivity | Restricted/secret data не включаются при default public/internal policy |
| Quality | Deterministic score = bounded success + recency; tie-break по `experience_id` |
| Budget | Одновременно ограничиваются `max_chars` и `max_items` |
| Explainability | Каждое исключение получает reason: `scope_denied`, `sensitivity_denied`, `char_budget`, `item_budget`, `provenance_digest_required` и т. п. |
| Safety boundary | Selector только выбирает данные; он не пишет memory, не запускает skill/tool и не выдаёт score за permission |

## Local verification

`tests/test_experience_reuse.py`: **4/4 passed** на CPython 3.14.7. Полный suite и security audits обязательны перед checkpoint.

Cross-agent leakage и external quality остаются отдельными gates; этот contract не заменяет OS sandbox и не является external A/B benchmark.
