# NOESIS 1.0 Next-Generation Primitives

This document describes the first implementation slice of `PLAN_NOESIS_1.0_MASTER_RU.md`. It is local-only and keeps the 0.5 stdlib core intact.

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
| Governed child runtime | `ChildExecutionRuntime`, `ExecutableSkillRuntime` | Versioned manifest, committed capability grant, shell-free argv, workspace containment, bounded environment/output/time and explicit hardened-backend requirement |
| Linux isolation backend | `BubblewrapBackend` | `--unshare-all`, `--unshare-net`, read-only system mounts, writable workspace only; unavailable backends fail closed |

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

## Gate 3 child-runtime contract

A child execution request is valid only when the parent has a committed `Gatekeeper` decision, the executable is allowlisted, the argv contains no inline-code switch, the workspace is real and traversal-free, environment keys are allowlisted, and time/output budgets are bounded. A request carrying a `SkillManifest` must match the skill identity, include every manifest capability in the explicit grant set, and use an available hardened sandbox backend. A missing grant, manifest identity mismatch or unavailable backend fails closed.

The Linux reference backend is `BubblewrapBackend`: it unshares namespaces and network, exposes read-only system mounts, binds only the workspace as writable, uses a fresh session and kills descendants on timeout. Adversarial tests verify host-path reads and outbound socket access are blocked. This is Linux evidence only; macOS and Windows native backend claims remain `not_run` until matching hosts are exercised.

`ContextManager` and `VaultProjector` do not execute content. Markdown is parsed as data and can only become memory through a caller-controlled promotion policy. `Gatekeeper` classifies and records a requested side effect but does not perform it. `ExecutionLadder` remains an availability contract, while `ChildExecutionRuntime` is the explicit process boundary and never imports or evaluates child/model-generated code.

## Verification

Run:

```text
python -m unittest discover -s tests -p 'test_*nextgen.py' -v
python -m unittest discover -s tests -p 'test_governance.py' -v
python -m unittest discover -s tests -v
```

The suites cover tamper detection, Windows SQLite cleanup, path denial, private-scope isolation, idempotency, compaction retention, gate approval, DAG cycles, atomic vault writes, staged skills, child-runtime manifest/grant enforcement, timeout/process-tree recovery, credential output blocking and adversarial Bubblewrap filesystem/network isolation. Native Windows/macOS sandbox evidence remains `not_run` until matching hosts are available.
