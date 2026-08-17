"""examples/memory_tiers.py

Demonstration of 4-tier memory + decay + offload.

Shows: Working -> Episodic -> Semantic -> Procedural flow,
hybrid FTS5 recall, Ebbinghaus decay, symbolic offload.

Run:  python examples/memory_tiers.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import Memory


def main():
    state_dir = os.path.join(os.path.dirname(__file__), "..", "_example_state")
    os.makedirs(state_dir, exist_ok=True)

    db_path = os.path.join(state_dir, "memory_tiers.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    mem = Memory(db_path)

    print("=" * 60)
    print("NOESIS 4-Tier Memory Demo")
    print("=" * 60)

    # ============================================================
    # TIER 1: WORKING — raw observations (bounded, per session)
    # ============================================================
    print("\n[1] WORKING TIER — raw observations")
    session = "demo-session-1"
    mem.observe(session, "inbound", "User asked: 'Can you dub my film to Spanish?'")
    mem.observe(session, "analysis", "Detected: film dubbing request, target ES")
    mem.observe(session, "action", "Queued Spanish dubbing pipeline")
    print(f"  Observations stored: {mem.stats()['observations']}")

    # ============================================================
    # TIER 2: EPISODIC — session summaries ("what happened")
    # ============================================================
    print("\n[2] EPISODIC TIER — session summaries")
    mem.summarize(session, "User requested Spanish dubbing for festival film; queued pipeline")
    print(f"  Summaries stored: {mem.stats()['summaries']}")

    # ============================================================
    # TIER 3: SEMANTIC — durable facts ("what I know")
    # ============================================================
    print("\n[3] SEMANTIC TIER — durable facts (dedup + strengthen)")
    # First save
    id1 = mem.save("client prefers European Spanish over Latin American", kind="semantic", confidence=0.9)
    print(f"  Saved fact: {id1[:8]}...")
    # Duplicate -> strengthens
    id2 = mem.save("client prefers European Spanish over Latin American", kind="semantic", confidence=0.8)
    print(f"  Duplicate save returned same id: {id1 == id2}")
    # Another fact
    mem.save("client's film is 90 minutes, festival deadline Oct 15", kind="semantic", confidence=0.7)
    mem.save("client budget: $2000 for full dubbing", kind="semantic", confidence=0.6)
    print(f"  Semantic memories: {mem.stats()['memories']}")

    # ============================================================
    # TIER 4: PROCEDURAL — workflows ("how to do it")
    # ============================================================
    print("\n[4] PROCEDURAL TIER — workflows with triggers")
    mem.save(
        "WHEN client requests dubbing THEN ask for reference audio and target language",
        kind="procedural", confidence=0.95
    )
    mem.save(
        "WHEN dubbing length > 1.25x slot THEN trigger compression pipeline",
        kind="procedural", confidence=0.9
    )
    print(f"  Total memories (semantic+procedural): {mem.stats()['memories']}")

    # ============================================================
    # HYBRID RECALL — FTS5 + substring fallback + strength ranking
    # ============================================================
    print("\n[5] HYBRID RECALL — FTS5 + substring + strength ranking")
    results = mem.recall("Spanish", limit=5)
    for r in results:
        print(f"  [{r['kind']}] strength={r['strength']:.2f} conf={r['confidence']:.2f} :: {r['fact'][:60]}...")

    # Access strengthens
    print("\n  Accessing 'Spanish' facts again (strength should increase)...")
    mem.recall("Spanish", limit=5)

    # ============================================================
    # EBBINGHAUS DECAY — strength *= 0.9^periods, floor 0.1
    # ============================================================
    print("\n[6] EBBINGHAUS DECAY — simulating 10 periods")
    for i in range(10):
        mem.decay(periods=1)
    profile = mem.profile(limit=5)
    for p in profile:
        print(f"  strength={p['strength']:.3f} :: {p['fact'][:50]}...")

    # ============================================================
    # SYMBOLIC OFFLOAD (TencentDB pattern)
    # ============================================================
    print("\n[7] SYMBOLIC OFFLOAD — long log -> refs/session.md")
    long_log = "# Session Log\n" + "\n".join([f"Line {i}: event data" for i in range(100)])
    ref_summary = mem.offload("session-offload-1", long_log, os.path.join(os.path.dirname(__file__), "..", "_example_state", "refs"))
    print(f"  Offloaded to refs/session-offload-1.md, summary id: {ref_summary[:8]}...")
    ref_path = os.path.join(os.path.dirname(__file__), "..", "_example_state", "refs", "session-offload-1.md")
    print(f"  Ref file size: {os.path.getsize(ref_path)} bytes")

    # ============================================================
    # FINAL STATS
    # ============================================================
    print("\n" + "=" * 60)
    print("FINAL STATS:", mem.stats())
    print("=" * 60)


if __name__ == "__main__":
    main()