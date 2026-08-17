# Recipe: Lead-processing loop with memory + leases

The core pattern from BotFarm: find a lead, remember its pain, claim it so no
other worker touches it, reply, and hand off. Uses all three primitives.

```python
import os
from noesis_harness import EventStore, Memory, Leases, Signals, Actions

state = "state"
os.makedirs(state, exist_ok=True)

es = EventStore(os.path.join(state, "events.jsonl"))
mem = Memory(os.path.join(state, "mem.db"))
leases = Leases(os.path.join(state, "leases.db"))
signals = Signals(os.path.join(state, "signals.db"))
actions = Actions(os.path.join(state, "actions.db"))


def process_lead(lead_id: str, text: str, worker: str) -> bool:
    # 1. Append the find event (auditable, idempotent).
    es.append("candidate_found", {"lead_id": lead_id, "text": text[:60]})

    # 2. Exclusive claim - one lead = one worker.
    claim = leases.acquire(lead_id, worker)
    if not claim["ok"]:
        print(f"{lead_id}: already held by {claim.get('holder')}")
        return False

    try:
        # 3. Remember the pain (deduped, searchable later).
        mem.save(f"{lead_id}: {text}", kind="semantic", confidence=0.8)
        mem.observe(lead_id, "inbound", text)

        # 4. Track the follow-up as a DAG action.
        action = actions.create(f"reply to {lead_id}")
        actions.complete(action)

        # 5. Notify the closer asynchronously.
        signals.send("director", f"{lead_id} replied", to_agent="closer")
        return True
    finally:
        leases.release(lead_id, worker)


process_lead("lead-1", "I need my film dubbed into Spanish", "worker-1")
process_lead("lead-1", "I need my film dubbed into Spanish", "worker-2")  # skipped
```

## What this gives you

- **Audit:** `es.iter_events()` shows the full chain for any lead.
- **No double-work:** the second worker is rejected by the lease.
- **No forgetting:** `mem.recall("Spanish")` finds the client's pain later.
- **Async handoff:** the closer picks up the signal on its next cycle.
