# Operator Case Bundle Runbook

Readiness-only bundle создаётся через `scripts/build_operator_case_bundle.py`. Он фиксирует case IDs, lane revisions, protocol fingerprint и security policy для последующего operator-run external comparison.

## Контракт

Artifact использует `noesis.operator-case-bundle.v1` и содержит deterministic manifest digest, bundle digest, required lanes, lane readiness states и bounded operator steps. Это export contract, а не executor.

| Поле | Требование |
|---|---|
| `mode` | Всегда `readiness_only`. |
| `execution_allowed` | Всегда `false`. |
| `automatic_execution` | Всегда `false`. |
| `approval_required` | Всегда `true` перед external command. |
| `network_policy` | `deny`. |
| `credentials` | `absent`. |
| `workspace_mode` | `disposable`. |
| `case_ids` | Уникальные, непустые и зафиксированные до execution. |

Complete manifest со всеми exact revisions получает `ready_for_operator_preflight`. Missing revision даёт `not_run`; unsafe policy, invalid schema, duplicate case IDs или malformed identity дают `blocked`. Ни один статус не запускает provider и не создаёт score.

## Последовательность оператора

Оператор проверяет manifest и bundle digests, подтверждает pinned executables и environment digests на matching host, получает explicit approval, запускает provider-neutral lane command в disposable workspace, ingest-ит signed lane receipt и case receipts, затем строит comparative report. Bundle не содержит provider credentials и сам не выполняет command.

Текущий repository bundle является только readiness artifact. Native Windows/macOS execution и Hermes/OpenCode/DeepSeek Harness execution остаются `not_run`, пока не доступны matching hosts, exact revisions, executables, disposable environments и explicit approval.

*Supplemental language: Russian.*
