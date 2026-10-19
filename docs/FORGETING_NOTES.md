# Forgetting: erasure that can be proven

**Added 2026-10-19.** `noesis_harness/forget.py`, `benchmarks/forget20.py`.

## Why this was built

The repo was idle for 50 days and the field moved. Four results published
between June and October 2026 make forgetting a measured property rather than
a claim:

| Work | Finding |
|---|---|
| **Bemula** (arXiv 2610.18052) | First benchmark for memory unlearning. Across six systems and three backbones, **no system passes more than 1.5% of forget requests end to end**; most score zero. Cause: the same fact lives in several derived forms, so deleting one copy leaves the rest. |
| **MemCut** (arXiv 2610.21405) | Two metrics that must not be confused — *native recovery* (what the system's own retriever returns) and *residual recovery* (what a reader recovers when handed every surviving object directly). Deleting a narrow selection leaves **39-76% residual recovery**; broad cut beats precise selection. Candidate coverage, not selection accuracy, is the bottleneck. |
| **Deployment-Time Memorization** (arXiv 2606.10062) | Forgetting Residue Score. Raw-only deletion leaves derived copies recoverable in **~20%** of cases; only a full-pipeline purge or tombstone redaction reaches zero. |
| **SAIHM** (IETF draft, 2026-10-11) | Erasure writes a receipt to a public log and appends the id to a public erasure list an observer can rebuild from those receipts. |

Before this work the package had **no erase path at all**: no
`Memory.delete`, no GDPR vocabulary anywhere, and `MemoryGraph` had no delete
method, so derived copies survived any erasure. The project was strong at
*proving what it did* (append-only logs, HMAC receipts, an independent
reviewer) and had no way to *remove* anything.

## The rule this changes

`AGENTS.md` rule 5 says "Never delete files — move to `_archive/`". That is
now qualified with a single exception, because archiving personal data on a
deletion request is not compliance, it is the opposite:

> **Sole exception: erasure demanded by law.** `forget.py` is the only
> sanctioned deletion path. Never add a second one.

## What it does

```python
from noesis_harness import Forger, build_predicate

forger = Forger(memory, graph=graph, lesson_journal=journal,
                receipt_path="receipts.jsonl")
receipt = forger.forget(build_predicate("sk-SECRET42"),
                        actor="operator:ann", reason="user_request")
forger.verify(receipt)   # {"forgotten": True, ...}
```

- **Erase by predicate, not by id.** MemCut's coverage finding is that you
  cannot know where the secret is, so the sweep runs over whole stores.
  Matching is case-, punctuation-, accent- and transliteration-insensitive:
  `sk-SECRET42`, `SK SECRET42` and `sk-Secret42` are one secret.
- **Covers every store it can reach** — `memories` (with its FTS index and
  vector column), `observations`, `summaries`, `graph` edges, and the
  append-only lesson journal. The receipt names the stores it actually
  covered, so a partial sweep is visible rather than reported as success.
- **Append-only stores are superseded, not rewritten.** The lesson journal
  keeps its line and its replay digest; the content becomes `[erased]`.
- **The proof never contains the secret.** Predicate tokens are stored as
  per-token digests, so a receipt naming `sk-SECRET42` cannot reproduce it.
  `content_digest()` does the same for the tombstone.
- **Residue is measured, two ways.** `native_hits` is what the system's own
  recall still serves; `residual_hits` is what survives when a reader is
  handed every object directly. The gap is `hidden_risk` — a lower bound on
  recoverable evidence the retriever happens not to surface today. A retriever
  that merely misses is not erasure.
- **Receipts and an erasure list, per SAIHM.** `verify_list()` reports whether
  the public list still agrees with the receipts, which catches a truncated or
  hand-edited list.

## The bench, and a defect it caught

`python benchmarks/forget20.py` plants a secret across 20 cases and store
combinations, forgets it, then probes **every store's own read API**.

The first version of the bench passed 20/20 while the graph store was never
wired — because it only called `memory.recall`. The secret was gone from
`memories` and still sitting in the graph as an edge, reachable by anyone
walking the graph. A bench that trusts the implementation's own word for
erasure proves nothing, which is the mistake the field reports.

After fixing the probe, two deliberate sabotages confirm it fails honestly:

| Sabotage | Result |
|---|---|
| graph store never wired | `forget_rate` drops to 0.65, 7 cases flagged, **FAIL** |
| erasure over-deletes bystanders | `preservation` drops to 0.0, **FAIL** |

Acceptance requires: forget rate 1.0, preservation 1.0, receipt completeness
1.0, worst hidden risk 0.0. Erasure that deletes more than it was asked to is
a failure, not thoroughness.

## Test coverage

`tests/test_forget.py`, 39 tests. Defects caught while writing them:

1. **The receipt contained the secret.** `build_predicate` defaulted its label
   to the raw phrase, so the proof of an erasure held the erased content —
   defeating the entire design. Fixed by digesting tokens.
2. **Digested predicates never matched.** The first digest implementation
   digested both sides incorrectly, so every sweep silently matched nothing.
3. **`matches` raised on a legit predicate** after a guard was added for
   mixed token forms; the guard was kept and the call path corrected.
4. **`Lesson` cannot be blanked.** Its validation rejects an empty cue, which
   is correct — the type refuses to represent "no lesson". Erasure therefore
   writes `[erased]`, a valid tombstone.

## What is still not solved

- **No coverage for the databases this module does not own.** A `LearningPromotionState`
  SQLite file, a `DomainLibrary` tree or a `SkillStore` root is outside these
  stores and can still hold the content. They need their own adapters; the
  receipt makes the gap visible rather than hiding it.
- **Deletion is a sweep, not a proof of unrecoverability.** SQLite pages,
  WAL segments and filesystem blocks may retain bytes after `DELETE`. The
  residue report measures *logical* reachability through this system's read
  paths. A deployment claiming cryptographic erasure needs SAIHM's key-destroy
  class, which is a different mechanism.
- **The bench is synthetic.** Bemula's own limitation is that its dialogues
  come from one generation pipeline; this bench is even narrower. It is a
  regression gate, not a benchmark result.