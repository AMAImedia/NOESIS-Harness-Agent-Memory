# Recipe: Human-in-the-loop gates

The 2026 anti-ban lesson: keyword->auto-reply is the fastest way to get an
account banned. Human-in-the-loop is a permanent architecture, not a flag.
Here is the pattern for gating any agent action behind a human approve step.

```python
import os
from noesis_harness import EventStore, Actions, Signals

state = "state"
es = EventStore(os.path.join(state, "events.jsonl"))
actions = Actions(os.path.join(state, "actions.db"))
signals = Signals(os.path.join(state, "signals.db"))

# 1. Agent drafts a reply -> creates a HITL action, tells the human
draft = actions.create("reply to lead-42", priority=8)
es.append("reply_drafted", {"lead": "lead-42", "action": draft})
signals.send("agent", "lead-42 draft ready for review", to_agent="human",
             type_="review")

# 2. Human approves (or rejects) - moves the DAG
#    approve: actions.complete(draft)  -> next action unblocks (auto-send)
#    reject:  actions.create("reject lead-42") ; complete it -> blocks send
actions.complete(draft)   # human clicked "approve"
es.append("reply_approved", {"lead": "lead-42", "by": "human"})

# 3. The send action auto-unblocked by the DAG, not by the agent itself
send = actions.create("send reply to lead-42", priority=9, requires=[draft])
print(actions.frontier())  # [send] - only after approval
```

## Rules that make this safe

1. **The agent never completes the send action itself.** Only the human
   completes the `requires` edge that unblocks sending.
2. **Every gate is an event.** `reply_drafted` / `reply_approved` /
   `reply_rejected` are audit entries; you can replay who approved what.
3. **Peer review as a second gate.** If an independent judge disagrees with
   the agent, route the draft back to the human instead of auto-sending:

```python
if peer_disagrees:
    signals.send("agent", f"peer disagrees on {draft}", to_agent="human",
                 type_="review_required")
    # do NOT complete draft
```

4. **Bounded turn budget.** Before each LLM step, check a quota
   (`es.project` of `budget_spent`); if exhausted, stop and ask the human
   (LoopX `spend-after-validated-writeback` pattern).

## Result

- Nothing is sent without a human (or an explicit `auto` flag per direction).
- The audit trail answers "why was this sent?".
- The loop cannot burn budget forever.
