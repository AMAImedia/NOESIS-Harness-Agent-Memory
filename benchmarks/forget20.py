"""Erasure bench: plant a secret, forget it, prove it is not extractable.

Deterministic, stdlib only, no LLM and no network. Stdlib-only and
deterministic are the point: the result has to be the same on every machine,
otherwise it is an anecdote rather than evidence.

    python benchmarks/forget20.py

Exit 0 only when every case is forgotten completely, nothing else was lost,
every receipt is complete and the hidden-risk share is zero.

What each case measures:

- **forgotten**    the secret is no longer extractable through any store.
- **preserved**    an unrelated bystander fact planted alongside the secret
                   still recalls afterwards. Erasure that deletes more than it
                   was asked to is a failure, not thoroughness.
- **complete**     the receipt names every store it covered. A partial sweep
                   reported as a success is the Bemula failure mode.
- **hidden risk**  the share of surviving evidence the retriever did not
                   surface, after MemCut. Zero is the only acceptable value:
                   a system that merely got lucky with its retriever has not
                   forgotten anything.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import Memory
from noesis_harness.forget import Forger, build_predicate, content_digest
from noesis_harness.graph import MemoryGraph


def _load(path=None):
    here = os.path.dirname(os.path.abspath(__file__))
    with open(path or os.path.join(here, "forget20.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _plant(case, memory, graph, spec):
    """Write the secret into every store the case names, plus a bystander."""
    nn = case["id"]
    secret = case["secret"]
    form = case.get("variant")
    if form:
        secret = spec["variant_forms"][form].replace("{nn}", "%02d" % nn)
    token = "sk-CASE%02d" % nn

    if "memory" in case["stores"]:
        memory.save(secret, "semantic")
    if "observation" in case["stores"]:
        memory.observe("session-%d" % nn, "chat", secret)
    if "summary" in case["stores"]:
        memory.summarize("session-%d" % nn, "summary of " + secret)
    if "graph" in case["stores"]:
        graph.link("owner-%d" % nn, "uses", token)

    bystander = spec["bystander"].replace("{nn}", "%02d" % nn)
    memory.save(bystander, "semantic")
    return secret, token, bystander


def _extractable(token, memory, graph, owner=None):
    """What is still reachable, through every public read path of every store.

    Each store is probed by its own read API rather than by one shared query:
    a secret that is gone from ``memories`` but still present as a graph edge
    is still recoverable by anyone who walks the graph, and a bench that only
    calls ``recall`` would score that as a clean erasure.
    """
    needle = token.lower()
    suffix = token.split("-")[-1].lower()
    hits = []

    def _carries(blob):
        text = str(blob).lower()
        return needle in text or suffix in text

    for hit in memory.recall(token, limit=50):
        if _carries(hit.get("fact", "")):
            hits.append(("memory", str(hit.get("id"))))

    if graph is not None:
        with graph._conn() as conn:
            rows = conn.execute("SELECT id, subj, pred, obj FROM edges").fetchall()
        for row in rows:
            if _carries("%s %s %s" % (row["subj"], row["pred"], row["obj"])):
                hits.append(("graph", str(row["id"])))
        # The graph's own traversal API, so a future change that stops writing
        # to the table but still serves the edge is caught here.
        if owner:
            try:
                for edge in graph.neighbors(owner):
                    if _carries("%s %s %s" % (edge["subj"], edge["pred"], edge["obj"])):
                        hits.append(("graph_api", str(edge["id"])))
            except Exception:
                pass

    with memory._conn() as conn:
        for row in conn.execute("SELECT id, content FROM observations"):
            if _carries(row["content"]):
                hits.append(("observations", str(row["id"])))
        for row in conn.execute("SELECT id, text FROM summaries"):
            if _carries(row["text"]):
                hits.append(("summaries", str(row["id"])))

    return sorted(set(hits))


def _bystander_recalls(bystander, memory):
    words = [w for w in bystander.split() if len(w) > 3]
    probe = words[-1] if words else bystander
    for hit in memory.recall(probe, limit=20):
        if bystander == hit.get("fact"):
            return True
    return False


def run(path=None):
    spec = _load(path)
    acceptance = spec["acceptance"]
    rows = []
    hit = 0
    preserved = 0
    complete = 0
    worst_hidden_risk = 0.0

    for case in spec["cases"]:
        tmp = tempfile.mkdtemp(prefix="noesis_f20_")
        memory = Memory(os.path.join(tmp, "m.db"))
        graph = MemoryGraph(os.path.join(tmp, "g.db"))
        forger = Forger(
            memory,
            graph=graph,
            receipt_path=os.path.join(tmp, "receipts.jsonl"),
        )

        secret, token, bystander = _plant(case, memory, graph, spec)

        predicate = build_predicate(token)
        receipt = forger.forget(predicate, actor="operator:bench", request_id="c%d" % case["id"])
        report = forger.residue(receipt.request_id)
        verify = forger.verify(receipt)

        # Two independent probes of the same property: the residue the forger
        # reports about itself, and a direct read of every store afterwards.
        # A bench that trusts the implementation's own word for it proves
        # nothing, which is exactly the mistake Bemula reports in the field.
        leaked = _extractable(token, memory, graph, owner="owner-%d" % case["id"])
        ok = not leaked and report.clean and report.hidden_risk == 0.0
        kept = _bystander_recalls(bystander, memory)

        hit += int(ok)
        preserved += int(kept)
        complete += int(receipt.complete)
        worst_hidden_risk = max(worst_hidden_risk, report.hidden_risk)

        rows.append(
            {
                "id": case["id"],
                "stores": case["stores"],
                "variant": case.get("variant", "plain"),
                "planted_digest": content_digest(secret),
                "matched": receipt.matched,
                "removed": receipt.removed,
                "forgotten": ok,
                "preserved": kept,
                "receipt_complete": receipt.complete,
                "residual": len(report.residual_hits),
                "native": len(report.native_hits),
                "hidden_risk": round(report.hidden_risk, 4),
                "leaked_rows": ["%s:%s" % pair for pair in leaked],
                "verified_forgotten": verify["forgotten"],
            }
        )

    n = len(spec["cases"])
    return {
        "schema_version": spec["schema_version"],
        "hit": hit,
        "n": n,
        "forget_rate": hit / float(n) if n else 0.0,
        "preservation": preserved / float(n) if n else 0.0,
        "receipt_completeness": complete / float(n) if n else 0.0,
        "worst_hidden_risk": round(worst_hidden_risk, 4),
        "acceptance": acceptance,
        "passed": bool(
            n
            and hit / float(n) >= acceptance["forget_rate"]
            and preserved / float(n) >= acceptance["preservation_min"]
            and complete / float(n) >= acceptance["receipt_completeness"]
            and worst_hidden_risk <= acceptance["hidden_risk_max"]
        ),
        "rows": rows,
    }


if __name__ == "__main__":
    out = run()
    width = max(len(str(row["id"])) for row in out["rows"])
    print("forget20 %s/%s cases" % (out["hit"], out["n"]))
    for row in out["rows"]:
        status = "ok " if row["forgotten"] else "LEAK"
        keep = "keep" if row["preserved"] else "LOST"
        print(
            "  case %-*s %-4s %-4s stores=%-2d removed=%-2d residual=%d hidden_risk=%.2f"
            % (
                width,
                row["id"],
                status,
                keep,
                len(row["stores"]),
                row["removed"],
                row["residual"],
                row["hidden_risk"],
            )
        )
    print(
        "  forget_rate=%.2f preservation=%.2f receipt_completeness=%.2f worst_hidden_risk=%.2f"
        % (
            out["forget_rate"],
            out["preservation"],
            out["receipt_completeness"],
            out["worst_hidden_risk"],
        )
    )
    print("PASS" if out["passed"] else "FAIL")
    sys.exit(0 if out["passed"] else 1)