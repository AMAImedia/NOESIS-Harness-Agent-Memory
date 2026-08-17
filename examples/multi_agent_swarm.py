"""examples/multi_agent_swarm.py

Three agents + coordination on a single EventStore.

Demonstrates: Leases (exclusive ownership), Signals (async mailbox),
Actions (DAG with auto-unblock) working together across agents.

Run:  python examples/multi_agent_swarm.py
"""

import os
import sys
import time
import threading
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import EventStore, Memory, Leases, Signals, Actions


def agent_worker(agent_id: str, state_dir: str, shutdown: threading.Event):
    """Worker agent: claims tasks, processes, emits signals."""
    es = EventStore(os.path.join(state_dir, "events.jsonl"))
    leases = Leases(os.path.join(state_dir, "leases.db"))
    signals = Signals(os.path.join(state_dir, "signals.db"))
    actions = Actions(os.path.join(state_dir, "actions.db"))

    while not shutdown.is_set():
        # 1. Try to claim an available action (frontier)
        action = actions.next()
        if not action:
            time.sleep(0.5)
            continue

        aid = action["id"]
        claim = leases.acquire(aid, agent_id)
        if not claim["ok"]:
            # Someone else got it
            time.sleep(0.2)
            continue

        # 2. Process the task (simulated)
        es.append("action_started", {"action_id": aid, "agent": agent_id, "title": action["title"]})

        # Simulate work
        work_time = random.uniform(0.1, 0.3)
        time.sleep(work_time)

        # 3. Complete action (auto-unblocks dependents)
        actions.complete(aid)
        leases.release(aid, agent_id)

        es.append("action_completed", {"action_id": aid, "agent": agent_id})
        signals.send(agent_id, f"completed {action['title']}", to_agent="supervisor", type_="result")

        print(f"[{agent_id}] completed: {action['title']}")


def supervisor_worker(state_dir: str, shutdown: threading.Event):
    """Supervisor: monitors progress, injects nudges via signals."""
    es = EventStore(os.path.join(state_dir, "events.jsonl"))
    signals = Signals(os.path.join(state_dir, "signals.db"))
    actions = Actions(os.path.join(state_dir, "actions.db"))

    cycle = 0
    while not shutdown.is_set():
        time.sleep(2.0)
        cycle += 1

        # Read inbox
        inbox = signals.read("supervisor")
        if inbox:
            for msg in inbox:
                es.append("supervisor_received", {"from": msg["from_agent"], "type": msg["type"]})

        # Periodic nudge: check for stuck actions
        counts = actions.counts()
        if counts.get("blocked", 0) > 3:
            signals.send("supervisor", "many blocked - consider priority bump", to_agent="", type_="nudge")

        if cycle % 3 == 0:
            # Inject a new high-priority task occasionally
            aid = actions.create(f"urgent-scan-{cycle}", priority=10)
            es.append("supervisor_injected", {"action_id": aid, "priority": 10})
            print(f"[supervisor] injected urgent task: {aid}")


def main():
    state_dir = os.path.join(os.path.dirname(__file__), "..", "_example_state")
    os.makedirs(state_dir, exist_ok=True)

    # Clean previous state
    for fname in ["events.jsonl", "leases.db", "signals.db", "actions.db"]:
        fpath = os.path.join(state_dir, fname)
        if os.path.exists(fpath):
            os.remove(fpath)

    es = EventStore(os.path.join(state_dir, "events.jsonl"))
    actions = Actions(os.path.join(state_dir, "actions.db"))

    # Seed initial task graph
    fetch = actions.create("fetch leads", priority=5)
    score = actions.create("score leads", requires=[fetch], priority=8)
    draft = actions.create("draft replies", requires=[score], priority=6)
    send = actions.create("send replies", requires=[draft], priority=7)

    es.append("system_start", {"tasks": [fetch, score, draft, send]})

    shutdown = threading.Event()

    # Start agents
    threads = []
    for i in range(3):
        t = threading.Thread(target=agent_worker, args=(f"worker-{i}", state_dir, shutdown), daemon=True)
        t.start()
        threads.append(t)

    sup_t = threading.Thread(target=supervisor_worker, args=(state_dir, shutdown), daemon=True)
    sup_t.start()
    threads.append(sup_t)

    # Run for a few seconds
    print("Running multi-agent swarm for 8 seconds...")
    time.sleep(8)
    shutdown.set()

    for t in threads:
        t.join(timeout=1.0)

    # Final state
    print("\n--- Final State ---")
    print("Events:", es.count())
    print("Actions:", actions.counts())
    print("Signals threads:", Signals(os.path.join(state_dir, "signals.db")).threads())


if __name__ == "__main__":
    main()