# Recipe: Event sourcing for audit and crash recovery

Every decision is an append-only event; the current state is a replay.
This gives you an audit trail and crash recovery for free (LoopX / deepseek-harness
pattern).

```python
import os
from noesis_harness import EventStore

es = EventStore("state/events.jsonl")

# Register reducers: (state, payload) -> state
es.register_reducer("reply_sent", lambda s, p: (s or 0) + 1)
es.register_reducer("reply_rejected", lambda s, p: (s or 0) - 1)

# Append events (idempotent on content fingerprint)
es.append("reply_sent", {"lead_id": "L1", "text": "sure, here's a demo"})
es.append("reply_sent", {"lead_id": "L2", "text": "happy to help"})
es.append("reply_rejected", {"lead_id": "L3", "reason": "off-topic"})

# Replay: current state = fold(events)
print(es.project(0))     # 1  (2 sent - 1 rejected)

# Idempotency: identical double-send is absorbed
es.append("reply_sent", {"lead_id": "L1", "text": "sure, here's a demo"})
print(es.project(0))     # still 1
```

## Audit a single decision

```python
# "Why did the bot reply to L1?"
for ev in es.iter_events():
    if ev["payload"].get("lead_id") == "L1":
        print(ev["type"], ev["payload"])
```

## Crash recovery

The log is append-only JSONL. A crash mid-write loses at most the last line
(which you can detect as a partial JSON and skip). On restart:

```python
es2 = EventStore("state/events.jsonl")   # reopens, reloads seen fingerprints
state = es2.project(0)                   # rebuilds exactly the same state
```

## Effect IDs for end-to-end traceability

Chain events with a shared `effect_id = cycle:candidate:reply` so a "found ->
scored -> replied" chain is one unit:

```python
effect = f"cycle-7:candidate-42:reply-1"
es.append("candidate_found", {"effect_id": effect, "candidate": 42})
es.append("candidate_scored", {"effect_id": effect, "score": 80})
es.append("reply_sent", {"effect_id": effect})
```

Grep the log by `effect_id` to replay the whole pipeline for one lead.
