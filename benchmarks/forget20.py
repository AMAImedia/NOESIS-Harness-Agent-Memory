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


def _reconstruction_probe(memory, parts, minimal):
    """Which parts survive, and whether the minimal combination is intact.

    MemCut's central case: the record that *states* the secret is deleted, and
    the secret is still identifiable from records that never state it. The
    minimal combination is the smallest subset that still implies it, so
    ``reconstructed`` is true when every member of that subset is readable.

    The parts deliberately exclude the token. Including it would make the check
    circular: the token is what the erasure names, so it would always be gone
    and reconstruction would always read as impossible.

    Returning the survivors rather than a boolean lets a failure name its own
    cause instead of just going red.
    """
    survivors = []
    for part in parts:
        probe = " ".join(word for word in part.split() if len(word) > 2) or part
        hits = " ".join(str(h.get("fact", "")) for h in memory.recall(probe, limit=20))
        if part.lower() in hits.lower():
            survivors.append(part)
    reconstructed = all(part in survivors for part in minimal)
    return survivors, reconstructed


#: Which case number the evidence-trail scenario uses. Fixed so the scenario
#: is reproducible and its planted text is stable across runs.
TRAIL_CASE_NN = 7


def _trail_scenarios(spec, nn):
    """Expand the configured scenarios into ``(id, token, parts, minimal)``.

    Each scenario is one shape of the MemCut problem: a token, records that
    never state it, and the minimal subset of those records that still implies
    it. Several shapes rather than one, because a single hand-written case
    proves only that one case works.
    """
    out = []
    for scenario in spec["evidence_trail"]["scenarios"]:
        def expand(value):
            return value.replace("{nn}", "%02d" % nn)

        out.append(
            (
                scenario["id"],
                expand(scenario["token"]),
                [expand(part) for part in scenario["parts"]],
                [expand(part) for part in scenario["minimal_combination"]],
            )
        )
    return out


def _run_trail(spec, acceptance):
    """Every MemCut scenario, each erased two ways.

    Run in two halves on purpose. The first shows what a caller gets who
    forgets only the literal secret: a clean receipt, zero logical residue, and
    the secret still reconstructable from the minimal combination. The second
    shows that naming the combination closes it. Reporting only the second
    would be the dishonest version of this bench.

    Every scenario must show both halves. A scenario where the naive erasure
    already reconstructs nothing has stopped testing anything, so it counts as
    a failure rather than a pass.
    """
    rows = []
    all_closed = True
    all_trapped = True

    for scenario_id, token, parts, minimal in _trail_scenarios(spec, TRAIL_CASE_NN):
        single_survivors, single_reconstructed = _one_trail_pass(
            token, parts, minimal, compound=False
        )
        compound_survivors, compound_reconstructed = _one_trail_pass(
            token, parts, minimal, compound=True
        )
        all_trapped = all_trapped and single_reconstructed
        all_closed = all_closed and not compound_reconstructed
        rows.append(
            {
                "id": scenario_id,
                "single_predicate": {
                    "surviving_parts": single_survivors,
                    "reconstructed": single_reconstructed,
                },
                "compound_predicate": {
                    "surviving_parts": compound_survivors,
                    "reconstructed": compound_reconstructed,
                },
            }
        )

    return {
        "cases": len(rows),
        "rows": rows,
        "single_predicate_reconstructs": all_trapped,
        "compound_predicate_reconstructs": not all_closed,
        "compound_reconstruction": 0.0 if all_closed else 1.0,
        "passed": bool(rows) and all_trapped and all_closed,
    }


def _one_trail_pass(token, parts, minimal, compound):
    """Plant the token and its supporting parts, then erase one way or the other."""
    tmp = tempfile.mkdtemp(prefix="noesis_f20t_")
    memory = Memory(os.path.join(tmp, "m.db"))
    memory.save(token, "semantic")
    for part in parts:
        memory.save(part, "semantic")
    forger = Forger(memory, receipt_path=os.path.join(tmp, "receipts.jsonl"))
    if compound:
        # Name every supporting element, not just the secret. MemCut's finding
        # is that a broad cut beats a precise one.
        predicate = build_predicate(token, extra_tokens=parts)
    else:
        predicate = build_predicate(token)
    forger.forget(predicate, actor="operator:bench", request_id="trail-%s" % compound)
    return _reconstruction_probe(memory, parts, minimal)


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
    trail = _run_trail(spec, acceptance)
    return {
        "schema_version": spec["schema_version"],
        "hit": hit,
        "n": n,
        "forget_rate": hit / float(n) if n else 0.0,
        "preservation": preserved / float(n) if n else 0.0,
        "receipt_completeness": complete / float(n) if n else 0.0,
        "worst_hidden_risk": round(worst_hidden_risk, 4),
        "acceptance": acceptance,
        "evidence_trail": trail,
        "passed": bool(
            n
            and hit / float(n) >= acceptance["forget_rate"]
            and preserved / float(n) >= acceptance["preservation_min"]
            and complete / float(n) >= acceptance["receipt_completeness"]
            and worst_hidden_risk <= acceptance["hidden_risk_max"]
            and trail["compound_reconstruction"] <= acceptance["compound_reconstruction_max"]
            and trail["passed"]
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
    trail = out["evidence_trail"]
    print(
        "  evidence-trail (MemCut): forget-by-secret alone reconstructs=%s, "
        "compound predicate reconstructs=%s"
        % (
            trail["single_predicate_reconstructs"],
            trail["compound_predicate_reconstructs"],
        )
    )
    print("PASS" if out["passed"] else "FAIL")
    sys.exit(0 if out["passed"] else 1)