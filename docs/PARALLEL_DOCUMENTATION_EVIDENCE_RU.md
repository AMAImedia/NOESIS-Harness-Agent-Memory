# Documentation Security и Link/Schema Evidence

**Статус:** локально verified  
**Runtime:** CPython 3.14.7 Linux  
**Machine-readable evidence:** `docs/PARALLEL_DOCUMENTATION_EVIDENCE.json`  
**Evidence SHA-256:** `1b29e185b22b12b1f23585e631082980565f26040ac0b460ce306f26f34dc6b3`

## Parallel lanes

| Lane | Проверка | Результат |
|---|---|---|
| `docs-security` | Markdown fenced examples: credential literals, pipe-to-shell, destructive commands, eval/exec, shell interpolation и privilege patterns | `passed`; high `0`, medium `0` |
| `markdown-links` | Local relative links без network; generated `runtime/` docs исключены из project scope | `passed`; 67 Markdown files, 28 local links, missing `0` |
| `json-evidence` | JSON parseability и `schema_version` для selected evidence/manifests | `passed`; 13 files, findings `0` |
| `ru-checklist` | Russian master checklist markers и paths к machine-readable evidence | `passed`; missing `[]` |

## Boundary

Проверка выполняется offline и read-only. Она не открывает external URLs, не публикует документы, не выполняет model-generated code и не заявляет external/native release evidence. Generated CPython runtime исключён из project Markdown-link scope, потому что его internal documentation не является NOESIS release documentation.

## Результат

Documentation security, local-link integrity и JSON evidence schemas закрыты локально. При добавлении новых Markdown/evidence files соответствующие links/schema markers должны оставаться в docs index и master checklist.
