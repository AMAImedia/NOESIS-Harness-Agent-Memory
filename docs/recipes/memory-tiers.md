# Recipe: Four-tier memory with decay and offload

Use all four memory tiers exactly like agentmemory + TencentDB:

- **Working** - raw observations as they arrive.
- **Episodic** - session summaries ("what happened").
- **Semantic** - durable facts ("what I know") with confidence + decay.
- **Procedural** - workflows ("how to do it") with trigger conditions.

```python
import os
from noesis_harness import Memory

mem = Memory("state/mem.db")

# 1. WORKING - raw observations
mem.observe("session-1", "inbound", "client needs Spanish film dubbing")

# 2. EPISODIC - session summary
mem.summarize("session-1", "client wants festival dubbing ES, 90min film")

# 3. SEMANTIC - durable facts (dedup + strengthen on re-save)
mem.save("client prefers European Spanish", kind="semantic", confidence=0.9)
mem.save("client prefers European Spanish", kind="semantic")  # strengthens, no dup

# 4. PROCEDURAL - workflow with trigger
mem.save(
    "WHEN client asks for price THEN send pricing link + offer free demo",
    kind="procedural", confidence=0.95
)

# 5. RECALL - hybrid FTS5 + substring + strength ranking
results = mem.recall("Spanish", limit=5)
for r in results:
    print(r["fact"], r["strength"])

# 6. DECAY - run periodically; old facts cool, accessed facts stay hot
mem.decay(periods=1)          # strength *= 0.9
mem.recall("Spanish")         # accessing strengthens again

# 7. OFFLOAD - long logs to refs/, keep only a pointer (TencentDB pattern)
mem.offload("session-1", big_log_text, "refs/")
```

## When to run decay

Decay is lazy on `recall()` and explicit via `decay()`. A sensible schedule
for a 24/7 agent:

- Call `decay(1)` once per hour (active facts stay hot).
- `decay(24)` once per day to cool old facts hard.
- Re-access (recall) cancels cooling for the accessed fact.

## Offload economics

TencentDB measured **-61% token savings** by offloading raw logs to `refs/*.md`
and keeping only a graph/pointer in context. Same idea here: the agent keeps
`offloaded -> refs/session-1.md` and greps the file by id when it needs detail.
