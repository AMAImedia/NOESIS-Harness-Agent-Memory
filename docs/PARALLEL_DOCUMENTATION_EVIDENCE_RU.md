# Documentation Security и Link/Schema Evidence

**Статус:** локально verified  
**Runtime:** CPython 3.14.7 Linux  
**Machine-readable evidence:** `docs/PARALLEL_DOCUMENTATION_EVIDENCE.json`  
**Evidence SHA-256:** `8065e0d1bf4cef5a8b4557b4cbbd5a68ffbfad8bd963ff6498c9a4ec97774df6`

## Parallel lanes

| Lane | Проверка | Результат |
|---|---|---|
| `docs-security` | Markdown fenced examples: credential literals, pipe-to-shell, destructive commands, eval/exec, shell interpolation и privilege patterns | `passed`; high `0`, medium `0` |
| `markdown-links` | Local relative links без network; generated `runtime/` docs исключены из project scope | `passed`; 75 Markdown files, 37 local links, missing `0` |
| `json-evidence` | JSON parseability и `schema_version` для selected evidence/manifests | `passed`; 15 files, findings `0` |
| `ru-checklist` | Russian master checklist markers и paths к machine-readable evidence | `passed`; missing `[]` |

## Boundary

Проверка выполняется offline и read-only. Она не открывает external URLs, не публикует документы, не выполняет model-generated code и не заявляет external/native release evidence. Generated CPython runtime исключён из project Markdown-link scope, потому что его internal documentation не является NOESIS release documentation.

## Результат

Documentation security, local-link integrity и JSON evidence schemas закрыты локально. При добавлении новых Markdown/evidence files соответствующие links/schema markers должны оставаться в docs index и master checklist.
