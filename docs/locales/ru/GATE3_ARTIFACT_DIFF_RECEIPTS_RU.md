# Gate 3 Artifact-Diff Receipts — русская локализация

Это supplemental-описание English primary contract для child-runtime execution assurance. Каждый receipted child run связывает request и policy digests с canonical before/after artifact manifest, deterministic artifact diff и signed execution receipt.

## Receipt binding

Child runtime снимает path-relative manifest до запуска child и после его завершения. Каждая file entry содержит relative path, byte size и SHA-256 content digest. Diff записывает added, removed и changed paths, а также canonical digest полного before/after payload. Receipt хранит этот diff digest и подписывает HMAC-SHA256 полный receipt digest.

| Boundary | Требование |
|---|---|
| Canonical paths | Manifest paths относительны declared workspace и сортируются до hashing. |
| Content integrity | Фиксируются file size и SHA-256; missing workspace отклоняется. |
| Receipt binding | `artifact_diff_digest` входит в signed stable payload receipt. |
| Tamper handling | Изменённое поле, signature или stored payload fail-closed отклоняются. |
| Replay handling | Existing request identity и recovery receipt checks остаются fail-closed. |
| Recovery honesty | Recovery record не заявляет rollback или restoration без подтверждения injected handler. |

Artifact diff доказывает только изменение configured workspace. Он не доказывает OS-level isolation, network isolation или semantic safety generated content. Native Windows/macOS и external harness A/B остаются `not_run` до matching hosts, exact revisions, disposable environments и signed operator-approved evidence.

English primary contract: [`GATE3_ARTIFACT_DIFF_RECEIPTS.md`](../../GATE3_ARTIFACT_DIFF_RECEIPTS.md).
