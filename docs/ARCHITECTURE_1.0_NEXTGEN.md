# NOESIS 1.0 Next-Generation Primitives

This document describes the first implementation slice of `PLAN_NOESIS_1.0_MASTER.md`. It is local-only and keeps the 0.5 stdlib core intact.

## What is implemented

| Primitive | Module | Guarantee |
|---|---|---|
| Run identity | `noesis_harness.nextgen.RunEnvelope` | Stable run/task/tenant/trace identity |
| Capability boundary | `CapabilityManifest` | Deny by default; filesystem roots and network hosts are explicit |
| Tamper-evident audit | `AuditChain` | JSONL hash chain with sequence/link verification |
| Idempotent commands | `DurableCommandLedger` | One command ID yields one committed result |
| Private agent scopes | `AgentManifest`, `IsolationBroker` | Messages and memory proposals are explicit; child cannot write parent private scope |
| Long context | `ContextManager` | Durable message tree, forks, non-destructive compaction, budgeted packing |
| Side-effect control | `governance.Gatekeeper` | Deny, stage/simulate, or approve; never claims a mutation happened |
| Multi-agent DAG | `DAGPlanner` | Deterministic stages, bounded parallelism, cycle rejection |
| Obsidian projection | `VaultProjector` | Atomic Markdown notes with stable IDs, tags and source IDs |
| Skill review | `SkillGate` | Stage → test → approve/reject; no automatic code activation |
| Execution ladder | `ExecutionLadder` | Workspace/simulation by default; missing sandbox is `unavailable` |

## Minimal example

```python
from noesis_harness import (
    AgentManifest, ContextManager, DAGPlanner, ExecutionLadder,
    Gatekeeper, ActionRequest, CapabilityManifest, VaultNote, VaultProjector,
)

# Each agent has a private scope. Shared state is explicit.
parent = AgentManifest("director", "director", private_scope="private:director", writable_scopes=("shared",))
researcher = AgentManifest("researcher", "research", parent_id="director", private_scope="private:researcher", readable_scopes=("shared",))

# Long context is durable and source-linked.
ctx = ContextManager("state.db")
sid = ctx.create_session("director")
ctx.add(sid, "user", "Investigate the task", source_ids=("request-1",))
ctx.set_block("director", "policy", "Cite evidence; do not mutate external systems.", 200)
window = ctx.pack(sid, 400, agent_id="director")

# Risky effects are staged, not faked.
cap = CapabilityManifest(operations=("fs_write",), filesystem_roots=("./workspace",))
gate = Gatekeeper()
request = ActionRequest("director", "fs_write", "./workspace/report.md", "write")
assert gate.decide(request, cap, simulation={"would_write": True})["status"] == "pending"

# Obsidian remains a reviewable projection with provenance.
vault = VaultProjector("vault")
vault.write(VaultNote("task-1", "Task 1", window["text"], ("task",), ("request-1",)))

# Missing hardened runtime is reported honestly.
assert ExecutionLadder().choose("sandbox")["status"] == "unavailable"
```

## Security boundaries

`ContextManager` and `VaultProjector` do not execute content. Markdown is parsed as data and can only become memory through a caller-controlled promotion policy. `Gatekeeper` classifies and records a requested side effect but does not perform it. `ExecutionLadder` is an availability contract, not a sandbox implementation: subprocess, browser and hardened sandbox adapters remain explicit future integrations.

## Verification

Run:

```text
python -m unittest discover -s tests -p 'test_*nextgen.py' -v
python -m unittest discover -s tests -p 'test_governance.py' -v
python -m unittest discover -s tests -v
```

The two new suites cover tamper detection, Windows SQLite cleanup, path denial, private-scope isolation, idempotency, compaction retention, gate approval, DAG cycles, atomic vault writes, staged skills and honest sandbox fallback.
