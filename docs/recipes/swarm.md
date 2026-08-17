# Recipe: Multi-agent swarm with coordination

Run 3 workers + a supervisor on one shared EventStore, with leases preventing
double-work and signals carrying async messages. This is the full example
from `examples/multi_agent_swarm.py` explained step by step.

```python
import os, threading, time
from noesis_harness import EventStore, Leases, Signals, Actions

state = "state"
es = EventStore(os.path.join(state, "events.jsonl"))
leases = Leases(os.path.join(state, "leases.db"))
signals = Signals(os.path.join(state, "signals.db"))
actions = Actions(os.path.join(state, "actions.db"))


def worker(name: str, stop: threading.Event):
    while not stop.is_set():
        task = actions.next()                 # highest-priority pending task
        if not task:
            time.sleep(0.5); continue
        claim = leases.acquire(task["id"], name)
        if not claim["ok"]:
            time.sleep(0.2); continue         # someone else took it
        try:
            es.append("task_started", {"task": task["id"], "agent": name})
            time.sleep(0.2)                   # do the work
            actions.complete(task["id"])      # auto-unblocks dependents
            leases.release(task["id"], name)
            es.append("task_done", {"task": task["id"], "agent": name})
            signals.send(name, f"done {task['title']}", to_agent="supervisor")
        except Exception:
            leases.release(task["id"], name)
```

## Why this does not need a leader

- **No dispatcher** - workers poll `actions.frontier()`; whoever claims first
  works. Leases make the claim exclusive.
- **No dead workers** - a lease expires (TTL), so a crashed worker's task is
  reclaimed by `leases.cleanup()` + the next poll.
- **No lost messages** - signals are durable in SQLite; a supervisor that was
  down reads them on restart.
- **No cycles** - completion auto-unblocks only real dependents; a task that
  completes is never re-picked.

## Scaling

- Add workers: just start more threads with different names. Leases do the
  arbitration.
- Add a supervisor: a process that reads `signals.read("supervisor")` and
  injects high-priority actions via `actions.create(title, priority=10)`.
