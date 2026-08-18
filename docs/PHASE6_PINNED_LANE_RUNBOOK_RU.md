# Phase 6 — Pinned Lane Operator Runbook

Этот runbook запускает три **раздельных** lanes. Hermes и OpenCode не импортируются в NOESIS и не становятся её зависимостями. Каждый lane должен выполняться в disposable environment с exact revision и отдельным result/evidence file.

## Preconditions

Перед запуском оператор обязан иметь:

| Поле | Требование |
|---|---|
| `SYSTEM_REVISION` | Непустой exact commit/tag/digest; placeholder запрещён |
| `TASK_MANIFEST_SHA256` | SHA-256 фактического `external_ab_manifest_v1.json` |
| `MODEL_PROVIDER` | Явно зафиксированный provider/model configuration |
| `WORKSPACE` | Уже созданная disposable directory; outside access denied |
| `RUNNER_ARGV` | Массив аргументов, не shell string |
| `EVIDENCE_KEY` | Runtime HMAC key длиной минимум 16 символов; в файл не записывается |

Если хотя бы одно поле неизвестно, результат должен быть `not_run`, а не `passed`.

## 1. Generate a lane spec

```bash
cd /path/to/NOESIS-Harness-Agent-Memory
PY314=/path/to/python3.14
MANIFEST=benchmarks/external_ab_manifest_v1.json
SHA256=$($PY314 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$MANIFEST")
mkdir -p /tmp/noesis-lanes/{noesis,hermes,opencode}

$PY314 scripts/external_runner_contract.py create \
  --system hermes \
  --revision '<EXACT_HERMES_COMMIT_OR_DIGEST>' \
  --task-manifest "$MANIFEST" \
  --argv '<PINNED_HERMES_RUNNER>' '--manifest' "$MANIFEST" '--workspace' /tmp/noesis-lanes/hermes \
  --output /tmp/noesis-lanes/hermes/spec.json
```

Для OpenCode замените только `--system`, exact revision, disposable workspace и pinned argv. Для NOESIS используется тот же manifest, но собственный NOESIS runner. Значения `<...>` нельзя оставлять: это намеренно невалидные placeholders.

Проверка spec:

```bash
$PY314 scripts/run_external_lane.py \
  --spec /tmp/noesis-lanes/hermes/spec.json \
  --workspace /tmp/noesis-lanes/hermes \
  --output /tmp/noesis-lanes/hermes/plan.json
```

Ожидается `execution: not_started` и `approval_required: true`.

## 2. Explicit execution

```bash
$PY314 scripts/run_external_lane.py \
  --spec /tmp/noesis-lanes/hermes/spec.json \
  --workspace /tmp/noesis-lanes/hermes \
  --output /tmp/noesis-lanes/hermes/result.json \
  --execute --approve --timeout 300
```

Без `--approve` процесс не запускается. Runner использует argv array, `shell=False`, bounded timeout и redaction output. Для каждого system запускается отдельный процесс и отдельная workspace.

## 3. Signed evidence ingestion

```bash
$PY314 scripts/ingest_runner_result.py \
  --spec /tmp/noesis-lanes/hermes/spec.json \
  --result /tmp/noesis-lanes/hermes/result.json \
  --key "$EVIDENCE_KEY" \
  --output /tmp/noesis-lanes/hermes/evidence.json
```

Evidence принимается только если identity fields, workspace, argv, metrics и schema совпадают со spec, credential-like content отсутствует, SHA-256/protocol fingerprint имеют строгий 64-hex формат, а execution/status согласованы: `not_started` или `denied` только с `not_run`; `started`, `completed` или `fixture_only` не могут иметь `not_run`. HMAC envelope успешно проверяется. HMAC envelope подтверждает controlled operator integrity; это не public release signature.

## 4. Acceptance gate

Comparative report разрешён только если для `noesis`, `hermes` и `opencode` одновременно присутствуют:

1. exact revision;
2. одинаковый manifest digest и protocol fingerprint;
3. disposable workspace evidence;
4. accepted signed evidence;
5. измеренные metrics или explicit `unsupported`/`not_run` с причиной.

До выполнения этих условий итоговый статус остаётся **external evidence pending**, и никакое превосходство над Hermes/OpenCode не заявляется.

## Текущий статус в этом checkout

Runner contract и synthetic evaluator проверены локально. Реальные pinned Hermes/OpenCode environments, exact revisions и operator-approved external executions отсутствуют; поэтому текущие Hermes/OpenCode records корректно имеют статус `not_run`.
