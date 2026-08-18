# Offline Release Audit

**Назначение:** локальный read-only audit перед release checkpoint.  
**Default mode:** offline; remote Git parity не вызывается.  
**Security boundary:** network=false, credentials=false, model-generated code не исполняется.

## Проверяемые области

| Область | Gate |
|---|---|
| Secret hygiene | Credential-like tokens/private-key markers в `noesis_harness/*.py` отсутствуют; synthetic holdout fixtures учитываются отдельно |
| AST safety | Реальные вызовы `eval`/`exec` отсутствуют; syntax errors отсутствуют |
| Package exports | Governance и execution exports доступны через `noesis_harness` |
| Git integrity | `git diff --check` проходит; финальный checkpoint имеет clean working tree |
| Russian checklist | Маркеры MA/API/EXEC/REL/NAT/CI присутствуют в master checklist |

`--remote` остаётся explicit opt-in для отдельной remote parity проверки. Offline audit никогда не вызывает `git ls-remote`, поэтому его можно безопасно выполнять в air-gapped/local-first lane.

## Verified result

После commit запускаются четыре SafeParallelExecutor lanes: secret/AST, package exports, Git integrity и русский checklist. Требование final report — **4/4 passed**, zero security findings, clean tree, four unique workspaces и remote parity disabled.

Этот audit не заявляет external Hermes/OpenCode execution и не заменяет Windows/macOS native evidence.
