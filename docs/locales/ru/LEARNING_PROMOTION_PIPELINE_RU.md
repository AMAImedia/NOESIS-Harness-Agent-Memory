# Human-Governed Learning Promotion Pipeline

Это supplemental-описание нормативного English contract для provenance-bound self-learning promotion. Pipeline является **review-first, approval-required, immutable, rollback-capable и non-executing**.

## Lifecycle

```text
experience receipt → deterministic holdout evaluation → review proposal
        → explicit approval → immutable version promotion
        → verification receipt → optional activation → rollback
```

| Состояние | Значение | Допустимый переход |
|---|---|---|
| `review` | Proposal прошёл deterministic holdout acceptance и ожидает review. | `approved` или `rejected` |
| `approved` | Explicit operator approval и approval tests прошли. | `promoted` или `blocked` |
| `promoted` | Immutable version записана и verification callback прошёл. | `rolled_back` |
| `rolled_back` | Active pointer удалён или восстановлен на предыдущую версию. | Terminal |
| `blocked` | Провален holdout, leakage, digest, approval или verification gate. | Terminal |
| `rejected` | Proposal отклонён оператором. | Terminal |

Receipt связывает experience ID, agent ID, scope, source/policy digests, outcome, payload digest, timestamp и schema version. Holdout принимается только при наличии хотя бы одного case, полном pass и нулевом leakage. Cases сортируются по `case_id` до hashing, поэтому digest deterministic.

Proposal остаётся review-only до explicit approval. Promotion отклоняет content digest mismatch, отсутствие approval, failed verification, duplicate version directory и исключения verification callback. Module не создаёт executable entrypoint и не запускает skill content.

Activation представлена только `ACTIVE` pointer на immutable version. Rollback удаляет pointer или восстанавливает предыдущий. Promotion receipt подписывается HMAC-SHA256 и проверяется constant-time comparison.

> Local promotion evidence доказывает только целостность lifecycle. Это не доказывает общую capability, защиту от всех prompt injections или superiority над другим агентом.

English primary contract: [`LEARNING_PROMOTION_PIPELINE.md`](../../LEARNING_PROMOTION_PIPELINE.md).
