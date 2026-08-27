# NOESIS-Harness-Agent-Memory — архитектура

> **Версия:** 0.5.0 · **Статус:** 67 unittest + recall20 20/20 · **Зависимости:** только stdlib

---

## Обзор

NOESIS-Harness-Agent-Memory — это **zero-dependency, local-first фреймворк координации агентов**, построенный из паттернов, извлечённых из 16+ продакшен-агентных систем (LoopX, agentmemory, TencentDB-Agent-Memory, Hermes Agent, agent-teams, deepseek-harness, evalscope и др.).

**Принцип дизайна:** детерминированное ядро (хранение, координация, replay) с LLM в качестве опционального pluggable-слоя. Никаких сетевых вызовов, никаких тяжёлых зависимостей, запускается на ноутбуке с 6 GB VRAM.

---

## Основные модули

```
noesis_harness/   # event_store, memory, coordination + 0.5 модули
                  # privacy snapshot consolidate procedures mesh inspect
                  # trace queue loop_guard graph budget hitl scope vfs session mcp_stdio
                  # __init__.py публичные экспорты
```

---

## Модуль 1: Event Store (`event_store.py`)

**Источник паттерна:** LoopX `event_sourced_state.py`, deepseek-harness `Session.append`

### Дизайн
- **Append-only JSONL** — одна строка на событие, crash-safe (частичная запись = потеря только последней строки)
- **Идемпотентный append** — отпечаток содержимого (SHA-256 от type + canonical JSON) предотвращает дубликаты
- **Детерминированная проекция** — state = fold(events) через зарегистрированные редьюсеры
- **Replay/debug/audit** — пересборка любого состояния из лога; нет скрытого мутируемого состояния

### Схема события
```json
{
  "event_id": "sha256-fingerprint-or-explicit",
  "type": "candidate_found | reply_drafted | reply_sent | budget_spent | ...",
  "payload": { ... },
  "seq": 42
}
```

### API
```python
es = EventStore("output/events.jsonl")
es.register_reducer("inc", lambda state, payload: (state or 0) + payload["n"])
es.append("inc", {"n": 1})                    # возвращает event_id
es.append("inc", {"n": 1})                    # идемпотентно, возвращён тот же id
es.project(0)                                 # → 2 (детерминированный replay)
```

### Идемпотентность
- Задан явный `event_id` → используется напрямую
- Нет `event_id` → используется отпечаток содержимого (type + canonical payload)
- Повторная отправка того же содержимого = no-op (поглощается на записи)

---

## Модуль 2: Memory (`memory.py`)

**Источник паттерна:** agentmemory (4 уровня), TencentDB-Agent-Memory (L0-L3 offload), Hermes Agent (SQLite FTS5)

### Четыре уровня

| Уровень | Таблица | Назначение | Удержание |
|------|-------|---------|-----------|
| **Working** | `observations` | Сырые входящие события по сессии | Ограничено по сессии |
| **Episodic** | `summaries` | Сводки сессии ("что произошло") | По сессии |
| **Semantic** | `memories` (kind=semantic) | Устойчивые факты ("клиент X хочет Y") | Decay (Эббингауз) |
| **Procedural** | `memories` (kind=procedural) | Процедуры ("как обрабатывать dubbing-лид") | Decay + trigger |

### Гибридный поиск
1. **FTS5 (BM25)** — основное ключевое слово по `memories.fact`
2. **Substring fallback** — для терминов, которые FTS5 плохо токенизирует (CJK, camelCase)
3. **Ранжирование strength/decay** — прочитанные факты усиливаются; decay по Эббингаузу `strength *= 0.9^periods` (нижний предел 0.1)

### Symbolic Offload (паттерн TencentDB)
Длинные логи сессий → `refs/<session_id>.md` на диск. Агент хранит в контексте только указатель/сводку. Когда нужна детализация, grep по ref через `node_id`. **Экономия -61% токенов** (по бенчмаркам TencentDB).

### API
```python
mem = Memory("output/mem.db")

# Working / Episodic
mem.observe("session-1", "inbound", "client needs Spanish dubbing")
mem.summarize("session-1", "client wants festival dubbing ES")

# Semantic / Procedural (dedup + strengthen)
mem.save("client prefers European Spanish", kind="semantic", confidence=0.9)
mem.save("always ask for reference audio before cloning", kind="procedural")

# Recall (гибридный FTS5 + substring, усиление на доступе)
mem.recall("dubbing", limit=5)

# Decay (периодически)
mem.decay(periods=1)

# Offload длинного лога на диск
mem.offload("session-1", big_log_text, "refs/")
```

---

## Модуль 3: Coordination (`coordination.py`)

**Источник паттерна:** agentmemory (leases.ts, signals.ts, actions.ts), LoopX (task_lease.py, claim_visibility.py)

### 3.1 Leases — эксклюзивное владение задачей
- **Одна задача = один агент** — TTL-ограниченная аренда предотвращает потерю работы при сбое
- **Acquire** → возвращает `{ok, holder, expires_at, renewed}`
- **Renew** → продление аренды (только держатель)
- **Release** → явная передача
- **Cleanup** → восстановление истёкших аренд (фоновая задача)
- TTL по умолчанию: 10 мин, максимум 1 час

```python
L = Leases("coordination.db", ttl=600)
claim = L.acquire("lead-42", "worker-1")   # {"ok": True, "holder": "worker-1", ...}
L.renew("lead-42", "worker-1")             # продление
L.release("lead-42", "worker-1")           # передача
L.cleanup()                                # восстановление истёкших
```

### 3.2 Signals — асинхронный mailbox
- **Broadcast** (пустой `to_agent`) или **направленные** (`to_agent="worker"`)
- **Треды** через `reply_to` / `thread_id`
- **Read receipts** (timestamp `read_at`)
- **TTL sweep** (по умолчанию 24 ч)

```python
S = Signals("coordination.db")
S.send("director", "new lead found", to_agent="worker", type_="task")
S.send("worker", "reply drafted", reply_to=thread_id, type_="result")
inbox = S.read("worker")                    # проставляет read_at
threads = S.threads()                       # список активных тредов
```

### 3.3 Actions — DAG задач с авторазблокировкой
- **Типы рёбер:** `requires` | `unlocks` | `gated_by` | `conflicts_with` | `spawned_by`
- **Авторазблокировка** — при завершении действия любой блокированный зависимый, чьи `requires` все выполнены, переходит `blocked → pending`
- **Frontier** — разблокированные действия, ранжированные по priority, затем age

```python
A = Actions("coordination.db")
a = A.create("fetch candidate")
b = A.create("score candidate", requires=[a])
c = A.create("draft reply", requires=[b])

A.complete(a)                               # b разблокируется автоматически
A.next()                                    # действие с наивысшим приоритетом в pending
A.frontier(5)                               # топ-5 готовых действий
```

---

## Диаграмма потока данных

```
┌─────────────────┐     append()      ┌──────────────────┐
│   Agent Work    │ ───────────────▶ │   EventStore     │  (append-only JSONL)
│  (find/score/   │                   │  - idempotent    │
│   reply/close)  │                   │  - fingerprint   │
└────────┬────────┘                   └────────┬─────────┘
         │                                     │
         ▼                                     ▼
┌─────────────────┐                   ┌──────────────────┐
│    Memory       │                   │  Projection      │
│  (4 уровня +    │                   │  (replay →       │
│   FTS5 + decay) │                   │   current state) │
└────────┬────────┘                   └──────────────────┘
         │
         ▼
┌─────────────────┐
│  Coordination   │
│  - Leases       │  (одна задача = один агент)
│  - Signals      │  (асинхронный mailbox)
│  - Actions      │  (DAG + авторазблокировка)
└─────────────────┘
```

---

## Гарантия zero-dependency

| Зависимость | Назначение | Альтернатива |
|------------|----------|-------------|
| `sqlite3` | Memory, Coordination | stdlib |
| `hashlib` | Отпечатки событий | stdlib |
| `json` | Сериализация | stdlib |
| `threading` | Блокировки | stdlib |
| `time` | TTL, timestamps | stdlib |
| `uuid` | Идентификаторы | stdlib |
| `os` | Пути, каталоги | stdlib |

**Нет:** numpy, requests, pandas, pydantic, yaml, toml, click, rich, tqdm и любых сторонних пакетов.

---

## LLM-интеграция (pluggable, опционально)

Ядро **никогда не вызывает LLM**. Сжатие/суммаризация — это callbacks:

```python
def llm_compress(text: str) -> str:
    # Здесь ваш вызов LLM (локальный или удалённый)
    return summary

mem = Memory("mem.db", compressor=llm_compress)  # опционально
```

---

## Сравнение с исходными системами

| Фича | LoopX | agentmemory | TencentDB | Hermes | NOESIS |
|---------|-------|-------------|-----------|--------|--------|
| Event sourcing | ✗ | ✗ | ✗ | ✗ | ✓ |
| 4-уровневая память | ✗ | ✗ | ✗ (L0-L3) | ✗ (только FTS5) | ✓ |
| Symbolic offload | ✗ | ✗ | ✓ (Mermaid) | ✗ | ✓ |
| Leases + TTL | ✗ | ✓ | ✗ | ✗ | ✓ |
| Signals (mailbox) | ✗ | ✓ | ✗ | ✗ | ✓ |
| Action DAG + unblock | ✗ | ✗ | ✗ | ✗ | ✓ |
| Zero deps | ✗ | ✗ (iii-engine) | ✗ | ✗ | ✓ |
| Local-first (без облака) | ✗ | ✗ | ✗ | ✗ | ✓ |
| VRAM-aware (6 GB) | ✗ | ✗ | ✗ | ✗ | ✓ (BotFarm) |

---

## Запуск примера

```bash
cd NOESIS-Harness-Agent-Memory
python examples/botfarm_lead.py
```

Вывод:
```
lead-1: processed. recalled=True
lead-2: processed. recalled=True
lead-3: processed. recalled=True

--- state summary ---
events: 3
memory: {'observations': 3, 'memories': 6, 'summaries': 0}
actions: {'done': 3}
signals inbox (closer): 3
```

---

## Тестирование

```bash
python -m unittest discover -s tests -v
# 67 тестов, все проходят (stdlib unittest, без зависимостей)
```