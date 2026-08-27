# NOESIS-Harness-Agent-Memory — справочник API

> **Версия:** 0.4.0 · **Пакет:** `noesis_harness` · **Python:** 3.9+

---

## Быстрый импорт

```python
from noesis_harness import EventStore, Memory, Leases, Signals, Actions
```

---

## EventStore

### `EventStore(path: str, reducers: Optional[Dict[str, Callable]] = None)`

Создаёт или открывает хранилище событий по пути `path` (JSONL-файл).

**Параметры:**
- `path` — путь в файловой системе к JSONL-логу
- `reducers` — опциональный словарь `event_type -> reducer_fn(state, payload)`

**Пример:**
```python
es = EventStore("output/events.jsonl", reducers={
    "counter": lambda s, p: (s or 0) + p["n"]
})
```

---

### `register_reducer(event_type: str, reducer: Callable) -> None`

Регистрирует reducer для типа события. Редьюсеры сводят `(state, payload) -> state` во время проекции.

```python
es.register_reducer("inc", lambda state, payload: (state or 0) + payload["n"])
```

---

### `append(event_type: str, payload: Any, event_id: Optional[str] = None) -> str`

Добавляет событие. Идемпотентно по `event_id` или отпечатку содержимого.

**Параметры:**
- `event_type` — строковая категория (например, `"candidate_found"`, `"reply_sent"`)
- `payload` — JSON-сериализуемый dict
- `event_id` — опциональный явный ключ идемпотентности; если опущен, используется отпечаток содержимого

**Возвращает:** event_id (переданный или вычисленный).

**Идемпотентность:**
- Тот же `event_id` → вторая запись не происходит, возвращается существующий id
- Нет `event_id` + идентичное содержимое → тот же отпечаток → вторая запись не происходит

```python
eid = es.append("candidate_found", {"lead_id": "L1", "text": "needs Spanish dub"})
eid2 = es.append("candidate_found", {"lead_id": "L1", "text": "needs Spanish dub"})
assert eid == eid2  # True, дубликат не записан
```

---

### `iter_events() -> Iterable[Dict[str, Any]]`

Возвращает все события в порядке добавления (от старых к новым).

```python
for ev in es.iter_events():
    print(ev["type"], ev["payload"])
```

---

### `project(initial: Any = None) -> Any`

Детерминированный replay: сводит все события через зарегистрированные редьюсеры в одно состояние.

```python
state = es.project(0)  # initial=0 для счётчика
```

---

### `count() -> int`

Возвращает количество уникальных событий в хранилище.

---

### `project_chain(reducers: Dict[str, Callable]) -> Callable[[Iterable[Dict], Any], Any]`

Строит автономную функцию проекции из словаря редьюсеров.

```python
runner = project_chain({"inc": lambda s, p: (s or 0) + p["n"]})
result = runner(es.iter_events(), initial=0)
```

---

## Memory

### `Memory(db_path: str)`

Создаёт или открывает хранилище памяти на базе SQLite по пути `db_path`.

```python
mem = Memory("output/mem.db")
```

---

### `observe(session_id: str, kind: str, content: str) -> str`

Записывает сырое наблюдение рабочей памяти. Возвращает id наблюдения.

```python
oid = mem.observe("session-1", "inbound", "client needs Spanish dubbing")
```

---

### `summarize(session_id: str, text: str) -> str`

Сохраняет эпизодическую сводку сессии. Возозвращает id сводки.

```python
sid = mem.summarize("session-1", "client wants festival dubbing ES")
```

---

### `save(fact: str, kind: str = "semantic", confidence: float = 0.5) -> str`

Сохраняет устойчивый факт или процедуру. Дедупликация по содержимому: идентичный факт усиливает существующую запись вместо создания дубликата.

**Параметры:**
- `fact` — текст факта/процедуры
- `kind` — `"semantic"` или `"procedural"`
- `confidence` — 0.0..1.0

```python
mid = mem.save("client prefers European Spanish", kind="semantic", confidence=0.9)
```

**Дедупликация:** Если `fact` уже существует, strength += 0.2 (cap 2.0), access_count++, возвращается существующий id.

---

### `recall(query: str, limit: int = 10, kind: str = "") -> List[Dict]`

Гибридный recall: FTS5 BM25 + substring-fallback. Результаты ранжируются по FTS5-score, затем по strength. У прочитанных записей strength увеличивается.

**Возвращает:** список dict с ключами `id, kind, fact, confidence, strength, access_count, last_accessed_at, created_at, score`.

```python
results = mem.recall("dubbing", limit=5, kind="semantic")
```

---

### `decay(periods: int = 1) -> int`

Применяет забывание по Эббингаузу: `strength *= 0.9^periods`, нижний предел 0.1. Возвращает количество изменённых строк. Вызывать периодически (например, ежедневным cron).

```python
changed = mem.decay(periods=1)
```

---

### `profile(kind: str = "semantic", limit: int = 20) -> List[Dict]`

Топ памяти по strength + access_count.

---

### `offload(session_id: str, log_text: str, ref_dir: str) -> str`

Записывает длинный лог в `refs/<session_id>.md`, сохраняет указатель-сводку. Возвращает id сводки. Зеркалирует symbolic offload из TencentDB.

```python
sid = mem.offload("session-1", big_log_text, "refs/")
# создаёт refs/session-1.md, возвращает id сводки
```

---

### `stats() -> Dict[str, int]`

Возвращает счётчики: `{"observations": n, "memories": n, "summaries": n}`.

---

## Leases

### `Leases(db_path: str, ttl: int = 600)`

Создаёт хранилище аренд. `ttl` в секундах (по умолчанию 600 = 10 мин, максимум 3600 = 1 час).

```python
L = Leases("coord.db", ttl=600)
```

---

### `acquire(task_key: str, holder: str) -> Dict[str, Any]`

Пытается захватить задачу. Возвращает dict:
- `ok: bool` — True, если захвачено
- `holder: str` — текущий держатель
- `expires_at: float` — unix timestamp
- `renewed: bool` — True, если этот вызов продлил существующую аренду

```python
claim = L.acquire("lead-42", "worker-1")
# {"ok": True, "holder": "worker-1", "expires_at": 1234567890.0, "renewed": True}
```

---

### `renew(task_key: str, holder: str) -> bool`

Продляет TTL аренды. Возвращает False, если не держатель или аренда истекла.

---

### `release(task_key: str, holder: str) -> bool`

Явное освобождение. Возвращает False, если не держатель.

---

### `cleanup() -> int`

Восстанавливает истёкшие аренды (выставляет status='expired'). Возвращает количество.

---

## Signals

### `Signals(db_path: str, ttl: int = 86400)`

Асинхронный mailbox. `ttl` в секундах (по умолчанию 24 ч).

```python
S = Signals("coord.db")
```

---

### `send(from_agent: str, payload: Any, to_agent: str = "", type_: str = "info", thread_id: str = "", reply_to: str = "") -> str`

Отправляет сигнал. Возвращает id сигнала.

**Параметры:**
- `to_agent` — пусто = broadcast; задано = направленный
- `type_` — `"info" | "task" | "result" | "nudge" | ...`
- `thread_id` — явный id треда; если пусто, выводится из `reply_to` или из нового uuid
- `reply_to` — id сигнала, на который это ответ (начинает тред)

```python
S.send("director", "new lead", to_agent="worker", type_="task")
S.send("worker", "done", reply_to=first_sig_id, type_="result")
```

---

### `read(agent: str, unread_only: bool = True, thread_id: str = "") -> List[Dict]`

Читает inbox агента `agent` (направленные + broadcast). Проставляет `read_at` у возвращённых сообщений.

**Возвращает:** список dict сигналов с полями `id, from_agent, to_agent, type, thread_id, payload, created_at, read_at, expires_at`.

```python
inbox = S.read("worker")
```

---

### `threads() -> List[Dict]`

Список активных тредов: `thread_id, n (количество), last (timestamp)`.

---

### `cleanup() -> int`

Удаляет истёкшие сигналы. Возвращает количество.

---

## Actions

### `Actions(db_path: str)`

Хранилище DAG задач.

```python
A = Actions("coord.db")
```

---

### `create(title: str, priority: int = 5, requires: Optional[List[str]] = None) -> str`

Создаёт действие. Если задан `requires`, статус = `"blocked"` до завершения всех зависимостей. Возвращает id действия (12-символьный hex).

```python
a = A.create("fetch lead")
b = A.create("score lead", requires=[a])
```

---

### `complete(aid: str) -> None`

Помечает действие выполненным. Автоматически разблокирует зависимых, у которых все `requires` выполнены.

---

### `frontier(limit: int = 0) -> List[Dict]`

Разблокированные (`"pending"`) действия, ранжированные по priority desc, затем age asc. `limit=0` = все.

---

### `next() -> Optional[Dict]`

Действие с наивысшим приоритетом в статусе pending, или None.

---

### `counts() -> Dict[str, int]`

Счётчики статусов: `{"pending": n, "blocked": n, "done": n, "cancelled": n}`.

---

## Пример: полный pipeline

```python
from noesis_harness import EventStore, Memory, Leases, Signals, Actions
import os

state = "output/state"
os.makedirs(state, exist_ok=True)

es = EventStore(os.path.join(state, "events.jsonl"))
mem = Memory(os.path.join(state, "mem.db"))
leases = Leases(os.path.join(state, "leases.db"))
signals = Signals(os.path.join(state, "signals.db"))
actions = Actions(os.path.join(state, "actions.db"))

# 1. Логируем находку
es.append("candidate_found", {"lead_id": "L1", "text": "needs Spanish dub"})

# 2. Эксклюзивный захват
claim = leases.acquire("L1", "worker-1")
if not claim["ok"]:
    print("already handled by", claim.get("holder"))
else:
    # 3. Запоминаем боль клиента
    mem.save("L1: needs Spanish film dubbing for festival", kind="semantic", confidence=0.9)
    mem.observe("L1", "inbound", "needs Spanish film dubbing for festival")

    # 4. Создаём follow-up, завершаем
    reply = actions.create("reply to L1")
    actions.complete(reply)

    # 5. Уведомляем closer
    signals.send("director", "L1 replied", to_agent="closer")

print("Events:", es.count())
print("Memory:", mem.stats())
print("Actions:", actions.counts())
```

---

## Обработка ошибок

Все методы выбрасывают стандартные исключения Python (`sqlite3.Error`, `json.JSONDecodeError`, `OSError` и т. п.) на невосстановимых сбоях. Идемпотентные пути (`append`, `acquire`) никогда не выбрасывают исключение на дубликате — возвращается существующий id/результат.

---

## Потокобезопасность

Все публичные методы потокобезопасны через внутренний `threading.Lock`. Соединения с SQLite короткоживущие (открываются на каждую операцию) с `PRAGMA journal_mode=WAL` и `busy_timeout=10000`.

---

## Версионирование

| Версия | Дата | Изменения |
|---------|------|-----------|
| 0.1.0 | 2026-08-14 | Начальное ядро (event_store, memory, coordination, 15 тестов) |
| 0.2.0 | 2026-08-14 | Документация, примеры, архитектура |
| 0.4.0 | 2026-08-14 | Vector/RRF, privacy, snapshot LWW, mesh, inspect, trace/judge, queue, loop guard |

---

## Расширения 0.4

```python
from noesis_harness import (
    PrivacyFilter, export_snapshot, import_snapshot,
    ConsolidationWorker, ProcedureRunner,
    Mesh, InspectUI, AgentTrace, HybridJudge,
    DurableQueue, LoopGuard,
)

mem = Memory("mem.db", privacy=PrivacyFilter(), compressor=lambda t: t)
export_snapshot(mem, "peers/a.json")
Mesh(mem, "peers", node_id="a").sync()
DurableQueue("q.db").enqueue({"job": "score-lead"})
LoopGuard().check("reply:same-text")
HybridJudge().judge(["draft one"])
```

`noesis-inspect --mem state/mem.db --events state/events.jsonl`