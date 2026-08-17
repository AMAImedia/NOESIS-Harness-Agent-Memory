# NOESIS-Harness-Agent-Memory — API Reference

> **Version:** 0.4.0 · **Package:** `noesis_harness` · **Python:** 3.9+

---

## Quick Import

```python
from noesis_harness import EventStore, Memory, Leases, Signals, Actions
```

---

## EventStore

### `EventStore(path: str, reducers: Optional[Dict[str, Callable]] = None)`

Create or open an event store at `path` (JSONL file).

**Parameters:**
- `path` — filesystem path to the JSONL log file
- `reducers` — optional dict `event_type -> reducer_fn(state, payload)`

**Example:**
```python
es = EventStore("output/events.jsonl", reducers={
    "counter": lambda s, p: (s or 0) + p["n"]
})
```

---

### `register_reducer(event_type: str, reducer: Callable) -> None`

Register a reducer for an event type. Reducers fold `(state, payload) -> state` during projection.

```python
es.register_reducer("inc", lambda state, payload: (state or 0) + payload["n"])
```

---

### `append(event_type: str, payload: Any, event_id: Optional[str] = None) -> str`

Append an event. Idempotent on `event_id` or content fingerprint.

**Parameters:**
- `event_type` — string category (e.g., `"candidate_found"`, `"reply_sent"`)
- `payload` — JSON-serializable dict
- `event_id` — optional explicit idempotency key; if omitted, content fingerprint used

**Returns:** The event_id (provided or computed).

**Idempotency:**
- Same `event_id` → no second write, returns existing id
- No `event_id` + identical content → same fingerprint → no second write

```python
eid = es.append("candidate_found", {"lead_id": "L1", "text": "needs Spanish dub"})
eid2 = es.append("candidate_found", {"lead_id": "L1", "text": "needs Spanish dub"})
assert eid == eid2  # True, no duplicate written
```

---

### `iter_events() -> Iterable[Dict[str, Any]]`

Yield all events in append order (oldest first).

```python
for ev in es.iter_events():
    print(ev["type"], ev["payload"])
```

---

### `project(initial: Any = None) -> Any`

Deterministic replay: fold all events through registered reducers into a single state.

```python
state = es.project(0)  # initial=0 for counter
```

---

### `count() -> int`

Return number of unique events in the store.

---

### `project_chain(reducers: Dict[str, Callable]) -> Callable[[Iterable[Dict], Any], Any]`

Build a standalone projection function from a reducer map.

```python
runner = project_chain({"inc": lambda s, p: (s or 0) + p["n"]})
result = runner(es.iter_events(), initial=0)
```

---

## Memory

### `Memory(db_path: str)`

Create or open a SQLite-backed memory store at `db_path`.

```python
mem = Memory("output/mem.db")
```

---

### `observe(session_id: str, kind: str, content: str) -> str`

Record a raw working-memory observation. Returns observation id.

```python
oid = mem.observe("session-1", "inbound", "client needs Spanish dubbing")
```

---

### `summarize(session_id: str, text: str) -> str`

Save an episodic session summary. Returns summary id.

```python
sid = mem.summarize("session-1", "client wants festival dubbing ES")
```

---

### `save(fact: str, kind: str = "semantic", confidence: float = 0.5) -> str`

Save a durable fact or procedure. Content-addressable deduplication: identical fact strengthens existing entry instead of creating duplicate.

**Parameters:**
- `fact` — the fact/procedure text
- `kind` — `"semantic"` or `"procedural"`
- `confidence` — 0.0..1.0

```python
mid = mem.save("client prefers European Spanish", kind="semantic", confidence=0.9)
```

**Deduplication:** If `fact` already exists, strength += 0.2 (capped at 2.0), access_count++, returns existing id.

---

### `recall(query: str, limit: int = 10, kind: str = "") -> List[Dict]`

Hybrid recall: FTS5 BM25 match + substring fallback. Results ranked by FTS5 score, then strength. Accessed entries have strength incremented.

**Returns:** List of dicts with keys: `id, kind, fact, confidence, strength, access_count, last_accessed_at, created_at, score`

```python
results = mem.recall("dubbing", limit=5, kind="semantic")
```

---

### `decay(periods: int = 1) -> int`

Apply Ebbinghaus decay: `strength *= 0.9^periods`, floor 0.1. Returns number of changed rows. Call periodically (e.g., daily cron).

```python
changed = mem.decay(periods=1)
```

---

### `profile(kind: str = "semantic", limit: int = 20) -> List[Dict]`

Top memories by strength + access_count.

---

### `offload(session_id: str, log_text: str, ref_dir: str) -> str`

Write long log to `refs/<session_id>.md`, save a summary pointer. Returns summary id. Mirrors TencentDB symbolic offload.

```python
sid = mem.offload("session-1", big_log_text, "refs/")
# creates refs/session-1.md, returns summary id
```

---

### `stats() -> Dict[str, int]`

Return counts: `{"observations": n, "memories": n, "summaries": n}`.

---

## Leases

### `Leases(db_path: str, ttl: int = 600)`

Create lease store. `ttl` in seconds (default 600 = 10 min, max 3600 = 1 hour).

```python
L = Leases("coord.db", ttl=600)
```

---

### `acquire(task_key: str, holder: str) -> Dict[str, Any]`

Try to claim a task. Returns dict:
- `ok: bool` — True if acquired
- `holder: str` — current holder
- `expires_at: float` — unix timestamp
- `renewed: bool` — True if this call extended an existing lease

```python
claim = L.acquire("lead-42", "worker-1")
# {"ok": True, "holder": "worker-1", "expires_at": 1234567890.0, "renewed": True}
```

---

### `renew(task_key: str, holder: str) -> bool`

Extend lease TTL. Returns False if not holder or lease expired.

---

### `release(task_key: str, holder: str) -> bool`

Explicit release. Returns False if not holder.

---

### `cleanup() -> int`

Reclaim expired leases (set status='expired'). Returns count.

---

## Signals

### `Signals(db_path: str, ttl: int = 86400)`

Async mailbox. `ttl` in seconds (default 24h).

```python
S = Signals("coord.db")
```

---

### `send(from_agent: str, payload: Any, to_agent: str = "", type_: str = "info", thread_id: str = "", reply_to: str = "") -> str`

Send a signal. Returns signal id.

**Parameters:**
- `to_agent` — empty = broadcast; set = directed
- `type_` — `"info" | "task" | "result" | "nudge" | ...`
- `thread_id` — explicit thread id; if empty, derived from `reply_to` or new uuid
- `reply_to` — signal id this replies to (starts a thread)

```python
S.send("director", "new lead", to_agent="worker", type_="task")
S.send("worker", "done", reply_to=first_sig_id, type_="result")
```

---

### `read(agent: str, unread_only: bool = True, thread_id: str = "") -> List[Dict]`

Read inbox for `agent` (direct + broadcast). Marks `read_at` on returned messages.

**Returns:** List of signal dicts with `id, from_agent, to_agent, type, thread_id, payload, created_at, read_at, expires_at`.

```python
inbox = S.read("worker")
```

---

### `threads() -> List[Dict]`

List active threads: `thread_id, n (count), last (timestamp)`.

---

### `cleanup() -> int`

Delete expired signals. Returns count.

---

## Actions

### `Actions(db_path: str)`

Task DAG store.

```python
A = Actions("coord.db")
```

---

### `create(title: str, priority: int = 5, requires: Optional[List[str]] = None) -> str`

Create an action. If `requires` given, status = `"blocked"` until all dependencies done. Returns action id (12-char hex).

```python
a = A.create("fetch lead")
b = A.create("score lead", requires=[a])
```

---

### `complete(aid: str) -> None`

Mark action done. Auto-unblocks dependents whose `requires` are all met.

---

### `frontier(limit: int = 0) -> List[Dict]`

Unblocked (`"pending"`) actions, ranked by priority desc then age asc. `limit=0` = all.

---

### `next() -> Optional[Dict]`

Highest-priority pending action, or None.

---

### `counts() -> Dict[str, int]`

Status counts: `{"pending": n, "blocked": n, "done": n, "cancelled": n}`.

---

## Example: Full Pipeline

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

# 1. Log find
es.append("candidate_found", {"lead_id": "L1", "text": "needs Spanish dub"})

# 2. Exclusive claim
claim = leases.acquire("L1", "worker-1")
if not claim["ok"]:
    print("already handled by", claim.get("holder"))
else:
    # 3. Remember client pain
    mem.save("L1: needs Spanish film dubbing for festival", kind="semantic", confidence=0.9)
    mem.observe("L1", "inbound", "needs Spanish film dubbing for festival")

    # 4. Create follow-up, complete
    reply = actions.create("reply to L1")
    actions.complete(reply)

    # 5. Notify closer
    signals.send("director", "L1 replied", to_agent="closer")

print("Events:", es.count())
print("Memory:", mem.stats())
print("Actions:", actions.counts())
```

---

## Error Handling

All methods raise standard Python exceptions (`sqlite3.Error`, `json.JSONDecodeError`, `OSError`, etc.) on unrecoverable failures. Idempotent paths (append, acquire) never raise on duplicate — they return the existing id/result.

---

## Thread Safety

All public methods are thread-safe via internal `threading.Lock`. SQLite connections are short-lived (opened per operation) with `PRAGMA journal_mode=WAL` and `busy_timeout=10000`.

---

## Versioning

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-08-14 | Initial core (event_store, memory, coordination, 15 tests) |
| 0.2.0 | 2026-08-14 | Docs, examples, architecture |
| 0.4.0 | 2026-08-14 | Vector/RRF, privacy, snapshot LWW, mesh, inspect, trace/judge, queue, loop guard |

---

## 0.4 extras

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