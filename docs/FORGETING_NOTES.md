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

## Round 2: the three gaps, closed and measured

The first version of this note listed three unsolved problems. Each was then
worked rather than restated, and one of the three turned out to be **wrong**.

### Gap 1 — stores outside the original five: closed

`Forger` now reaches eight stores. The three new ones:

| Store | How it is reached | What was tricky |
|---|---|---|
| `SkillStore` | every file under `skills/`, every version | Sweeping only the *active* version would leave a rollback target intact — a secret in a superseded skill would survive an erasure that reported itself complete. Pointer files (`active.json`) hold ids and digests, so they are left alone. |
| `DomainLibrary` | every file under the domain directory, then `rebuild_index()` | `entry.json` is structured data. Tombstoning it as plain text made `rebuild_index()` unable to parse the entry, so the library reported itself **empty** — a tombstoned entry looked like one that never existed. It is now tombstoned as JSON, keeping its id and a digest of what was removed. |
| `DurablePromotionState` | the `record_json` column of every governance table | See below: this one produced the correction. |

**The correction.** The first note claimed a secret could be sitting in
`LearningPromotionState`. Measuring the schema showed that **no field in any
promotion record carries raw content**: `ExperienceReceipt`,
`HoldoutEvaluation` and `PromotionProposal` all store `*_digest` values, and
the evaluator-manifest table stores a digest too. The store is covered, and the
coverage finds nothing because there is nothing to find. `test_no_record_field_carries_raw_content`
asserts that property directly, so the claim is checked rather than remembered.

The sweep is still wired up as defence in depth, and a planted row is caught
(see `test_a_planted_secret_is_found_and_tombstoned`), because a future change
that starts storing content should not silently reopen the hole.

### Gap 2 — bytes that outlive rows: measured, and bounded honestly

Two mechanisms, one report:

- **`harden_sqlite()`** sets `secure_delete=ON`, runs
  `wal_checkpoint(TRUNCATE)` and then `VACUUM`. `Forger` calls it after every
  erasure by default (`harden=True`). The three steps do different jobs: the
  pragma zeroes freed pages, the checkpoint folds and truncates the WAL, and
  the vacuum rebuilds the file so pre-erasure freelists are not carried
  forward.
- **`scan_raw_bytes()`** reads bytes, not records, and is case-insensitive and
  token-aware. This is what closes the gap the logical report cannot see.

Demonstrated on a real file: 400 rows containing a secret are deleted, a
logical query returns `0` — and the raw scan still finds the secret in the
file. After `harden_sqlite()`, the scan finds nothing. Without that
demonstration, "we delete the rows" would have been a claim with a hole in it.

**What this is not.** It is not cryptographic erasure. See the next section.

### Gap 3 — the bench was too narrow: widened, and it caught a real defect

`benchmarks/forget20.py` now runs an **evidence-trail scenario** modelled on
MemCut: a token is planted in full, plus four supporting records that never
state it (a holder, an issuer, a reference, a date). The bench runs the
scenario twice:

| Erasure | Result |
|---|---|
| by the literal secret alone | **secret reconstructable** — a clean receipt, zero logical residue, and the account still fully identifiable |
| by the secret plus the supporting parts | not reconstructable |

Both halves are required to pass. Reporting only the second would be the
dishonest version of this bench, because the first is the failure the field
actually reports.

Writing it caught a defect in `build_predicate`: `extra_tokens` were appended
**whole**, so a widening written as a phrase (`"holder Ada Lovelace"`) became a
single token that matched nothing. A widening that silently does nothing is
the worst kind of failure in an erasure. Extras are now tokenized like
everything else.

## What is still genuinely not solved

- **Cryptographic erasure is impossible in this build, by rule.** Python's
  standard library has key-derivation (`hashlib.scrypt`, `hashlib.pbkdf2_hmac`)
  but **no symmetric cipher and no AEAD**. Under the zero-dependency rule the
  only honest erasure class is *access control*: content is withdrawn from
  every read path and its bytes are zeroed, but an attacker with a pre-erasure
  copy can still read it. `cipher_capability()` reports this, and
  `CellCipher.seal()` / `.destroy_key()` **raise** rather than pretend. A false
  claim of cryptographic erasure is worse than an honest access-control one,
  because it cannot be audited afterwards. Real cryptographic erasure needs
  SAIHM's key-destroy class, which needs a third-party cipher.
- **Filesystem blocks and backups are outside this module.** `VACUUM` rewrites
  the database file, but the old file's blocks may survive on the storage
  device, and nothing here reaches a backup, a snapshot or a replica. That is
  a deployment concern, not a library one, and a receipt should not imply
  otherwise.
- **The bench is synthetic.** Bemula's own limitation is that its dialogues come
  from one generation pipeline; this bench is narrower still. It is a
  regression gate, not a benchmark result.
- **The evidence-trail scenario has one shape.** It tests "secret plus four
  supporting facts". MemCut's real corpus annotates minimal evidence
  combinations per secret; reproducing that properly needs their dataset, not a
  hand-written case.