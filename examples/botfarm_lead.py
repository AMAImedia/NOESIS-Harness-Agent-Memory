"""examples/botfarm_lead.py

Worked example: a minimal lead-processing loop using all three primitives.

It mirrors how the real NOESIS BotFarm works (find -> score -> reply -> wait),
but as a self-contained 30-line loop, to show the harness in action.

Run:  python examples/botfarm_lead.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import EventStore, Memory, Leases, Signals, Actions


def main():
    state_dir = os.path.join(os.path.dirname(__file__), "..", "_example_state")
    os.makedirs(state_dir, exist_ok=True)

    es = EventStore(os.path.join(state_dir, "events.jsonl"))
    mem = Memory(os.path.join(state_dir, "mem.db"))
    leases = Leases(os.path.join(state_dir, "leases.db"))
    signals = Signals(os.path.join(state_dir, "signals.db"))
    actions = Actions(os.path.join(state_dir, "actions.db"))

    # Simulate three incoming leads.
    leads = [
        ("lead-1", "I need my film dubbed into Spanish for a festival"),
        ("lead-2", "Looking for lip-sync dubbing for a game trailer"),
        ("lead-3", "Do you localize corporate training videos to Hindi?"),
    ]

    for lead_id, text in leads:
        # 1. Log the find event (append-only, auditable).
        es.append("candidate_found", {"lead_id": lead_id, "text": text[:60]})

        # 2. Exclusive claim so two workers can't both handle it.
        claim = leases.acquire(lead_id, "worker-1")
        if not claim["ok"]:
            print(f"{lead_id}: already held by {claim.get('holder')} - skip")
            continue

        # 3. Remember the client's pain (deduped, searchable later).
        mem.save(f"{lead_id}: {text}", kind="semantic", confidence=0.8)
        mem.observe(lead_id, "inbound", text)

        # 4. Create a follow-up action, then complete the reply step.
        reply = actions.create(f"reply to {lead_id}")
        actions.complete(reply)

        # 5. Notify the closer (async mailbox).
        signals.send("director", f"{lead_id} replied", to_agent="closer")

        print(f"{lead_id}: processed. recalled={bool(mem.recall('dub'))}")

    print("\n--- state summary ---")
    print("events:", es.count())
    print("memory:", mem.stats())
    print("actions:", actions.counts())
    print("signals inbox (closer):", len(signals.read("closer")))


if __name__ == "__main__":
    main()
