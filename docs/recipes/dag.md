# Recipe: Task DAG with auto-unblock

Model a pipeline as a graph: `fetch -> [score, classify] -> draft -> check -> send`.
Dependents stay `blocked` until all `requires` are satisfied; completing a task
auto-unblocks them (agentmemory `actions.ts` pattern).

```python
import os
from noesis_harness import Actions

actions = Actions("state/actions.db")

fetch    = actions.create("fetch candidates", priority=5)
score    = actions.create("score candidates", priority=8, requires=[fetch])
classify = actions.create("classify direction", priority=7, requires=[fetch])
draft    = actions.create("draft replies", priority=6, requires=[score, classify])
check    = actions.create("compliance check", priority=5, requires=[draft])
send     = actions.create("send approved", priority=9, requires=[check])

# Only 'fetch' is pending; everything else is blocked.
print(actions.frontier())   # [fetch]

actions.complete(fetch)     # score + classify auto-unblock
print(actions.frontier())   # [score (pri=8), classify (pri=7)]

actions.complete(score)
actions.complete(classify)  # draft unblocks (both requires now done)
print(actions.frontier())   # [draft]

actions.complete(draft)     # check unblocks
actions.complete(check)     # send unblocks (highest priority)
print(actions.next())       # send
```

## Edge types

| Edge | Meaning | Blocks? |
|------|---------|---------|
| `requires` | to_id needs from_id done | yes |
| `unlocks` | from_id enables to_id (advisory) | no |
| `gated_by` | external gate (human approval) | no (advisory) |
| `conflicts_with` | don't run simultaneously | no (advisory) |
| `spawned_by` | provenance | no |

The DAG planner uses `requires` for unblocking. The others are metadata for
schedulers that want more control (e.g., GPU conflict hints).

## Claiming work

Workers claim with `actions.claim(aid, agent)` (pending -> active, atomic):

```python
if actions.claim(draft, "worker-1"):
    ...  # only one worker gets this
```

Completed tasks are never re-queued, so a retry of `complete()` is a no-op
(idempotent by design).
