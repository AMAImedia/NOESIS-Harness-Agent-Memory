# NOESIS 1.0 — примитивы следующего поколения

Этот документ описывает первый срез реализации `PLAN_NOESIS_1.0_MASTER_RU.md`. Документ локальный и сохраняет ядро 0.5 на базе stdlib.

## Что реализовано

| Примитив | Модуль | Гарантия |
|---|---|---|
| Run identity | `noesis_harness.nextgen.RunEnvelope` | Стабильная идентичность run/task/tenant/trace |
| Capability boundary | `CapabilityManifest` | Deny по умолчанию; filesystem roots и network hosts заданы явно |
| Tamper-evident audit | `AuditChain` | JSONL hash-chain, верификация sequence/link |
| Идемпотентные команды | `DurableCommandLedger` | Один command id даёт один зафиксированный результат |
| Приватные области агента | `AgentManifest`, `IsolationBroker` | Сообщения и предложения по памяти явные; ребёнок не может писать в private-область parent |
| Long context | `ContextManager` | Устойчивое дерево сообщений, форки, неразрушающая компрессия, бюджетированная упаковка |
| Контроль side-effect | `governance.Gatekeeper` | Deny, stage/simulate или approve; никогда не заявляет, что мутация произошла |
| Multi-agent DAG | `DAGPlanner` | Детерминированные стадии, ограниченный параллелизм, отклонение циклов |
| Obsidian-проекция | `VaultProjector` | Атомарные Markdown-заметки со стабильными id, тегами и source id |
| Skill review | `SkillGate` | Stage → test → approve/reject; никакой автоматической активации кода |
| Execution ladder | `ExecutionLadder` | Workspace/simulation по умолчанию; отсутствующий sandbox = `unavailable` |
| Governed child runtime | `ChildExecutionRuntime`, `ExecutableSkillRuntime` | Версионированный manifest, зафиксированный capability grant, shell-free argv, ограничение workspace, ограниченные environment/output/time и явное требование hardened-backend |
| Linux isolation backend | `BubblewrapBackend` | `--unshare-all`, `--unshare-net`, read-only system mounts, writable только workspace; недоступные backends fail-closed |
| Execution evidence | `ExecutionReceiptStore`, `ExecutionRecoveryStore` | HMAC-подписанное сохранение receipt, идемпотентный replay, явные состояния running/interrupted/recovered; recovery никогда не заявляет rollback без реальной операции rollback |
| Patch review | `PatchReviewStore`, `WorkspaceManager` | Устойчивые added/modified/deleted patch-предложения и статус review; авторизация merge остаётся отдельной и никогда не применяет файлы |
| Operator recovery | `ExecutionRecoveryAction`, `ExecutionRecoveryExecutor` | Аутентифицированный rollback/recover action проверяет подписанный receipt, одобренный patch, идентичность run и свежий base; инжектируемый handler должен подтвердить фактическую мутацию до изменения состояния |
| Multi-agent work product | `MultiAgentWorkProductLoop`, `WorkProductEnvelope` | Типизированный делегированный результат, владение workspace у каждого агента, независимый review, авторизация merge по свежему base, явный commit marker и устойчивый resume/replay |
| Параллельная устойчивость и доказательства | `SafeParallelExecutor`, `CrossAgentLeakageSuite`, `WorkProductBenchmarkEvaluator` | Явный лимит retry с reclaim действия, cancellation non-retry, 12 детерминированных cross-agent leakage holdouts и отдельные метрики correctness/delivery/leakage/recovery/reviewer-time |
| Workload benchmark | `MultiAgentWorkloadRunner`, `DurableWorkloadAggregator` | Несколько параллельных детерминированных lane, инъекция сбоев before write/after write/after read, ограниченный retry, агрегация результатов в SQLite/WAL, повторный replay, отклонение content-conflict и повторный percentile-отчёт |
| Active delegation leakage | `ActiveDelegationLeakageSuite` | Параллельные sibling-read/write, absolute-path и traversal-пробы остаются denied при активных нескольких lane |
| Доказательства качества памяти | `MemoryQualityEvaluator` | Отдельные метрики recall, attribution precision, conflict resolution, temporal order, compaction retention, hard budget и leakage-free; никакого скрытого model grading |

## Минимальный пример

```python
from noesis_harness import (
    AgentManifest, ContextManager, DAGPlanner, ExecutionLadder,
    Gatekeeper, ActionRequest, CapabilityManifest, VaultNote, VaultProjector,
)

# У каждого агента своя private-область. Общее состояние — явное.
parent = AgentManifest("director", "director", private_scope="private:director", writable_scopes=("shared",))
researcher = AgentManifest("researcher", "research", parent_id="director", private_scope="private:researcher", readable_scopes=("shared",))

# Long context устойчив и связан с источником.
ctx = ContextManager("state.db")
sid = ctx.create_session("director")
ctx.add(sid, "user", "Investigate the task", source_ids=("request-1",))
ctx.set_block("director", "policy", "Cite evidence; do not mutate external systems.", 200)
window = ctx.pack(sid, 400, agent_id="director")

# Рискованные эффекты стадируются, а не фейкуются.
cap = CapabilityManifest(operations=("fs_write",), filesystem_roots=("./workspace",))
gate = Gatekeeper()
request = ActionRequest("director", "fs_write", "./workspace/report.md", "write")
assert gate.decide(request, cap, simulation={"would_write": True})["status"] == "pending"

# Obsidian остаётся reviewable projection с provenance.
vault = VaultProjector("vault")
vault.write(VaultNote("task-1", "Task 1", window["text"], ("task",), ("request-1",)))

# Отсутствующий hardened runtime сообщается честно.
assert ExecutionLadder().choose("sandbox")["status"] == "unavailable"
```

## Контракт child-runtime Gate 3

Запрос child execution валиден только когда у parent есть зафиксированное решение `Gatekeeper`, executable находится в allowlist, argv не содержит inline-code switch, workspace существует и не содержит traversal, ключи environment в allowlist, бюджеты time/output ограничены. Запрос, несущий `SkillManifest`, должен совпадать с identity skill, включать каждую manifest capability в явный grant set и использовать доступный hardened sandbox backend. Отсутствующий grant, несовпадение manifest identity или недоступный backend — fail-closed.

Linux-референс backend — `BubblewrapBackend`: он unshare'ит namespaces и network, экспонирует read-only system mounts, bind'ит только workspace как writable, использует свежую сессию и убивает потомков по таймауту. Adversarial-тесты проверяют, что чтение host-path и outbound socket-доступ заблокированы. `ExecutionReceiptStore` подписывает и сохраняет результат, а `ExecutionRecoveryStore` явно фиксирует прерванную работу после рестарта. `PatchReviewStore` сохраняет состояние review, но не выполняет merge и не публикует patch'и. Это доказательство только для Linux; претензии на macOS и Windows native backend остаются `not_run` до прогонов на соответствующих хостах.

`ContextManager` и `VaultProjector` не исполняют содержимое. Markdown парсится как данные и может стать памятью только через caller-controlled promotion policy. `Gatekeeper` классифицирует и фиксирует запрошенный side-effect, но не выполняет его. `ExecutionLadder` остаётся контрактом доступности, тогда как `ChildExecutionRuntime` — это явный process boundary и никогда не импортирует и не выполняет дочерний/модельно-сгенерированный код. `ExecutionRecoveryExecutor` никогда не выводит rollback из review или receipt: требуются аутентифицированное действие оператора, проверка свежего base и подтверждение handler. `MultiAgentWorkProductLoop` никогда не позволяет агенту-исполнителю одобрить собственную работу, никогда не применяет файлы в ходе review и трактует commit как отдельно авторизуемый task-state marker.

## Верификация

Запуск:

```text
python -m unittest discover -s tests -p 'test_*nextgen.py' -v
python -m unittest discover -s tests -p 'test_governance.py' -v
python -m unittest discover -s tests -v
```

Наборы покрывают: tamper detection, Windows SQLite cleanup, отказ в path, изоляцию private-scope, идемпотентность, compaction retention, gate approval, DAG-циклы, атомарные vault-записи, стадированные skills, принуждение manifest/grant child-runtime, HMAC receipt persistence/tamper rejection, durable patch review, восстановление прерванного run, восстановление по таймауту/process-tree, блокировку credential output, adversarial Bubblewrap filesystem/network isolation, типизированные multi-agent work products, независимый review, отказ по устаревшему base, явный commit и resume/replay сессии, ограниченный retry/reclaim, cancellation non-retry, 12-case cross-agent leakage holdouts, детерминированные метрики качества work product, параллельную workload crash-инъекцию в трёх точках, отказ active-lane в workspace escape, durable aggregation replay/conflict rejection, повторный percentile-отчёт, четыре одновременные пробы active-delegation leakage и метрики качества памяти для recall, attribution, conflict, temporal order, compaction retention, hard budget и leakage-free поведения. Доказательства native Windows/macOS sandbox остаются `not_run` до появления соответствующих хостов.