"""examples/dag_actions.py

Actions DAG with dependencies + auto-unblock propagation.

Demonstrates: task graph, typed edges (requires/unlocks/conflicts_with),
auto-unblock on completion, priority frontier.

Run:  python examples/dag_actions.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import Actions


def print_state(actions: Actions, label: str):
    counts = actions.counts()
    frontier = actions.frontier(5)
    print(f"\n[{label}]")
    print(f"  counts: {counts}")
    print(f"  frontier (top 5):")
    for a in frontier:
        print(f"    - {a['id'][:8]}: {a['title']} (pri={a['priority']})")


def main():
    state_dir = os.path.join(os.path.dirname(__file__), "..", "_example_state")
    os.makedirs(state_dir, exist_ok=True)

    db_path = os.path.join(state_dir, "dag_actions.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    A = Actions(db_path)

    print("=" * 60)
    print("ACTIONS DAG DEMO — typed edges + auto-unblock")
    print("=" * 60)

    # Build a realistic pipeline DAG
    # fetch -> [score, classify] -> [draft_reply, check_compliance] -> send
    print("\n[1] Building DAG...")

    fetch = A.create("fetch candidates from sources", priority=5)
    score = A.create("score candidates", priority=8, requires=[fetch])
    classify = A.create("classify direction", priority=7, requires=[fetch])

    draft = A.create("draft replies", priority=6, requires=[score, classify])
    check = A.create("compliance check", priority=5, requires=[draft])

    send = A.create("send approved replies", priority=9, requires=[check])

    # Add conflict edge: can't score and classify same candidate in parallel
    with A._lock, A._conn() as c:
        c.execute(
            "INSERT INTO action_edges (from_id, to_id, kind) VALUES (?,?,?)",
            (score, classify, "conflicts_with")
        )

    print_state(A, "INITIAL")

    # Complete fetch -> score + classify should unblock
    print("\n[2] Completing 'fetch'...")
    A.complete(fetch)
    print_state(A, "AFTER fetch")

    # Complete score -> classify still blocked by conflicts_with? No, conflicts_with is advisory.
    # In this implementation, only 'requires' edges block. conflicts_with is metadata.
    print("\n[3] Completing 'score'...")
    A.complete(score)
    print_state(A, "AFTER score")

    # Complete classify -> draft unblocks (requires both score + classify)
    print("\n[4] Completing 'classify'...")
    A.complete(classify)
    print_state(A, "AFTER classify")

    # Complete draft -> check unblocks
    print("\n[5] Completing 'draft'...")
    A.complete(draft)
    print_state(A, "AFTER draft")

    # Complete check -> send unblocks (highest priority)
    print("\n[6] Completing 'check'...")
    A.complete(check)
    print_state(A, "AFTER check")

    # Complete send
    print("\n[7] Completing 'send'...")
    A.complete(send)
    print_state(A, "AFTER send")

    # ============================================================
    # Demonstrate priority + edge types
    # ============================================================
    print("\n" + "=" * 60)
    print("EDGE TYPES DEMO: requires | unlocks | gated_by | conflicts_with | spawned_by")
    print("=" * 60)

    db2 = os.path.join(os.path.dirname(__file__), "..", "_example_state", "dag_actions2.db")
    if os.path.exists(db2):
        os.remove(db2)
    B = Actions(db2)

    # requires (blocking)
    a1 = B.create("step A", priority=5)
    a2 = B.create("step B (requires A)", priority=5, requires=[a1])
    print(f"\nrequires: A={B.counts()}, B blocked={B.counts().get('blocked', 0)}")

# unlocks (reverse of requires - metadata only)
    a3 = B.create("step C")
    a4 = B.create("step D (unlocked by C)", priority=5)
    with B._lock, B._conn() as c:
        c.execute(
            "INSERT INTO action_edges (from_id, to_id, kind) VALUES (?,?,?)",
            (a3, a4, "unlocks")
        )
    print(f"unlocks: C done, D still pending (unlocks is metadata)")

    # gated_by (external gate - metadata)
    a5 = B.create("step E (gated by human approval)")
    a6 = B.create("step F")
    with B._lock, B._conn() as c:
        c.execute(
            "INSERT INTO action_edges (from_id, to_id, kind) VALUES (?,?,?)",
            (a5, a6, "gated_by")
        )
    print(f"gated_by: E done, F still pending (gated_by is metadata)")

    # conflicts_with (advisory - don't run simultaneously)
    a7 = B.create("task X (heavy GPU)")
    a8 = B.create("task Y (heavy GPU)")
    with B._lock, B._conn() as c:
        c.execute(
            "INSERT INTO action_edges (from_id, to_id, kind) VALUES (?,?,?)",
            (a7, a8, "conflicts_with")
        )
    print(f"conflicts_with: X and Y marked as conflicting (scheduler hint)")

    # spawned_by (provenance)
    a9 = B.create("parent task")
    a10 = B.create("child task")
    with B._lock, B._conn() as c:
        c.execute(
            "INSERT INTO action_edges (from_id, to_id, kind) VALUES (?,?,?)",
            (a9, a10, "spawned_by")
        )
    print(f"spawned_by: child task provenance tracked")

    print("\n" + "=" * 60)
    print("DAG COMPLETE — all patterns demonstrated")
    print("=" * 60)


if __name__ == "__main__":
    main()