# Зачем NOESIS-Harness-Agent-Memory?

> **Краткий ответ:** это единственный zero-dependency, local-first фреймворк координации агентов, который сочетает event-sourced state, 4-уровневую память с symbolic offload и полную multi-agent координацию (leases + signals + actions) — всё это в ~1 KB stdlib Python.

---

## Проблема

Хочется запустить команду агентов 24/7 на ноутбуке (6 GB VRAM, без облака, без API-ключей). Существующие варианты:

| Фреймворк | Зависимости | Local-first | Event sourcing | 4-уровневая память | Координация | VRAM-aware |
|-----------|------|-------------|----------------|---------------|--------------|------------|
| **Hermes Agent** | 70+ инструментов, тяжёлый | да | нет | нет (только FTS5) | Инструмент Delegate | нет |
| **agent-teams** | Hermes + больше | да | только TaskQueue | нет | да (swarm) | нет |
| **OpenClaw** | 100+ MB | да | нет | нет | нет | нет |
| **LoopX** | Control plane | да | да | нет | Claims+leases | нет |
| **agentmemory** | iii-engine | да | да | да | да (полная) | нет |
| **TencentDB** | LLM для сжатия | да | да | да (L0-L3) | нет | нет |
| **deepseek-harness** | Cordis/plugins | да | да | нет | Capability seam | нет |
| **evalscope** | Тяжёлые eval-зависимости | да | нет | нет | только Judge | нет |
| **MetaGPT / XAgent / Qwen-Agent** | Тяжёлые | Cloud-first | нет | нет | Role-based | нет |
| **Claude Code / Codex** | Проприетарные | нет | нет | нет | только Subagents | нет |
| **NOESIS** | **только stdlib** | **да** | **да** | **да** | **да** | **да** |

---

## Что отличает NOESIS

### 1. **Zero dependencies = zero friction**
```bash
# Никаких pip install, venv, docker, npm, cargo
python examples/botfarm_lead.py
# Просто работает. 15 тестов проходят на stdlib unittest.
```
Никаких `pip install`, `npm install`, `docker pull`, `cargo build`. Весь фреймворк — **~15 KB** stdlib Python. Clone → run → готово.

### 2. **Event-sourced state = audit + replay + crash-safe**
```python
# Каждое решение — append-only событие
es.append("reply_sent", {"lead_id": "L1", "text": "..."})
# Сбой? Ребут → es.project() восстанавливает точное состояние
# Аудит? grep events.jsonl по запросу "почему бот ответил X?"
```
- **Append-only JSONL** — crash-safe (частичная запись = потеря только последней строки)
- **Идемпотентный append** — повтор = no-op (fingerprint dedup)
- **Детерминированная проекция** — state = fold(events) → идеальный replay/debug
- **Effect IDs** — цепочки `cycle:candidate:reply` для сквозной трассируемости

### 3. **4-уровневая память + symbolic offload = долгосрочный recall**
| Уровень | Назначение | Механизм |
|------|---------|-----------|
| Working | Сырые входящие по сессии | таблица `observations` |
| Episodic | Сводки сессии | таблица `summaries` |
| Semantic | Устойчивые факты + confidence | `memories` (kind=semantic) + FTS5 |
| Procedural | Процедуры + триггеры | `memories` (kind=procedural) + decay |

**Гибридный поиск:** FTS5 (BM25) + substring fallback + ранжирование strength/decay.
**Decay:** Эббингауз `strength *= 0.9^periods` (нижний предел 0.1).
**Symbolic offload:** длинные логи → `refs/<id>.md` на диск, агент хранит указатель. **-61% токенов** (паттерн TencentDB).

```python
mem.save("client prefers European Spanish", kind="semantic", confidence=0.9)
mem.offload("session-42", huge_log, "refs/")  # записывает refs/42.md, хранит указатель
mem.recall("dubbing")  # FTS5 + substring + strength ranking
```

### 4. **Реальная multi-agent координация (не просто "делегация")**

| Примитив | Назначение | Источник паттерна |
|-----------|---------|----------------|
| **Leases** | Эксклюзивное TTL-владение задачей | agentmemory + LoopX |
| **Signals** | Асинхронный mailbox (broadcast, треды, receipts) | agentmemory |
| **Actions** | DAG с `requires` + авторазблокировка | agentmemory + LoopX |

```python
# Одна задача = один агент (lease)
lease = leases.acquire("lead-42", "worker-1")  # блокирует остальных

# Асинхронная коммуникация
signals.send("director", "new lead", to_agent="worker")

# DAG задач с авторазблокировкой
a = actions.create("fetch")
b = actions.create("score", requires=[a])
actions.complete(a)  # b разблокируется автоматически
```

**Нет центрального диспетчера** — агенты координируются peer-to-peer через leases + signals. Если агент падает, leases истекают и работа забирается заново.

### 5. **Local-first, VRAM-aware (доказательство — NOESIS BotFarm)**
Этот фреймворк не теоретический — он питает **NOESIS BotFarm**, работающий 24/7 на ноутбуке с **6 GB RTX 3060**:
- 0.8B резидентные модели + 9B swap через VRAM-менеджер
- 100% локально (без API-ключей, без облака)
- Human-in-the-loop gate (draft → approve → send)
- Durable queue + loop guard (портировано из agent-teams)

> **Ни один другой open-source фреймворк не запускает полноценную команду агентов + локальные LLM на 6 GB VRAM.**

### 6. **Детерминированное ядро, LLM опционально**
Фреймворк **никогда не вызывает LLM**. Сжатие/суммаризация — опциональные pluggable callbacks:

```python
def my_llm_compress(text): ...
mem = Memory("mem.db", compressor=my_llm_compress)  # опционально!
```

Никаких обязательных LLM-зависимостей, никаких API-ключей для работы ядра.

### 7. **Battle-tested паттерны, а не академические идеи**
Каждый паттерн извлечён из **продакшен-систем**:
- **Durable queue + loop guard** → портировано из agent-teams (hermes-swarm), работает в NOESIS BotFarm с 2026
- **Event sourcing** → LoopX `event_sourced_state.py` + deepseek-harness `Session.append`
- **4-уровневая память + гибридный поиск** → agentmemory (наиболее полная open-impl)
- **Symbolic offload** → TencentDB-Agent-Memory (измеренный -61% токенов)
- **Leases + signals + actions** → agentmemory (наиболее полная координация)
- **Agent trace + hybrid judge** → evalscope `llm_recall`

---

## Честное сравнение: что у нас пока нет

| Фича | Статус |
|---------|--------|
| Векторный поиск + RRF | Выпущено (опциональные backends, stdlib fallback) |
| Folder/HTTP mesh LWW | Выпущено (`Mesh`, `serve_mesh`) |
| Inspect UI | Выпущено (`InspectUI`, `noesis-inspect`) |
| Privacy + snapshot | Выпущено |
| Queue + loop guard | Выпущено |
| Cloud vendor deploy | Не цель (local-first) |

---

## Заявка "Best GitHub"

> **NOESIS = фреймворк, который позволяет ЛЮБОМУ разработчику с ноутбуком запустить локально устойчивую, координированную команду агентов — без облака, без API-ключей, без 100 MB зависимостей.**

Мы не конкурируем по "самому большому числу фич" или "самому большому сообществу". Мы конкурируем по **честной полезности для local-first разработчика**:
- Clone → run за 5 секунд
- 15 тестов, 0 зависимостей, 15 KB ядро
- Паттерны с provenance (каждый модуль ссылается на источник)
- Запускает NOESIS BotFarm 24/7 на ноутбуке с 6 GB
- MIT, только stdlib, только английский, без эмодзи

---

## Начало работы за 30 секунд

```bash
git clone https://github.com/AMAImedia/NOESIS-Harness-Agent-Memory
cd NOESIS-Harness-Agent-Memory
python examples/botfarm_lead.py
# events: 3
# memory: {'observations': 3, 'memories': 6, 'summaries': 0}
# actions: {'done': 3}
# signals inbox (closer): 3
```

---

## Источники (Provenance)

Каждый модуль документирует свои исходные паттерны. Внутренние research-заметки живут рядом с этим репозиторием во время разработки; публикуемое дерево самодостаточно (`docs/`).

| Модуль | Основные источники |
|--------|-----------------|
| `event_store.py` | LoopX `event_sourced_state.py`, deepseek-harness `Session.append` |
| `memory.py` | agentmemory (4 уровня), TencentDB-Agent-Memory (offload), Hermes Agent (FTS5) |
| `coordination.py` | agentmemory (leases/signals/actions), LoopX (task_lease/claims) |

---

## Лицензия

MIT — используйте, форкайте, стройте на основе. Атрибуция не требуется, но provenance приветствуется.