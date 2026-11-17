# AGENTS.md — NOESIS Harness Agent Memory

Instructions for AI coding agents working in this repo.

## Rules (hard)

1. **Zero dependencies** — the `noesis_harness/` package must stay stdlib-only
   (`sqlite3`, `hashlib`, `json`, `threading`, `time`, `uuid`, `os`, `math`).
   No numpy, no requests, no pandas. This is the whole point: local-first, no
   install friction.
2. **Deterministic core, LLM optional** — storage/recall/coordination never call
   an LLM. If you add compression, it must be a pluggable callback, not a hard
   dependency.
3. **Append-only state** — never mutate the event log. State is always a replay
   projection. If you need a new fact, append an event, don't edit an old one.
4. **Idempotency on every write path** — `event_id` fingerprints, content dedup,
   TTL leases. A double-send must be a no-op, not a duplicate.
5. **Never delete files** — move to `_archive/<name>_<date>` instead.
   **Sole exception, added 2026-10-19: erasure demanded by law.** When a user
   or a regulator requires personal data to be erased, archiving it is not
   compliance — it is the opposite. `noesis_harness/forget.py` is the only
   sanctioned deletion path. It is required to leave evidence that is *not*
   the erased content: a tombstone saying what was erased, when, and on whose
   request, plus a public receipt list, so the deletion is provable without the
   data being recoverable. Never add a second deletion path, and never make
   erasure reach outside the coverage `forget.py` defines.
6. **Tests with every change** — `python -m unittest discover -s tests -q` must
   stay green (67+). Also `python benchmarks/recall20.py` and
   `python benchmarks/forget20.py`. No external test deps.

## Style

- Python 3.9+ compatible (no `X | None` syntax in signatures, no `match`).
- English only in code/comments. No emoji.
- Each module starts with a docstring naming the systems it borrows patterns
  from (provenance matters for this project).
- Typed statuses as string enums, not scattered booleans.

## Provenance discipline

Every non-trivial module documents its source patterns (LoopX, agentmemory,
TencentDB, deepseek-harness, Hermes, agent-teams). When you port a new pattern,
add the source to the module docstring and to `../RESEARCH_DAIGEST.md`.

## Owner communication (recorded 2026-09-18)

- The repository owner is not a programmer (student). Explain every change in
  plain language, no jargon, with a simple "what changed and why".
- Chat replies to the owner MUST be in Russian. Code, docstrings, comments,
  commit messages, and repository documentation stay English.
- Before starting a non-trivial task, restate your understanding and ask for
  confirmation first.
- End every work batch with an honest "before -> after" report in simple terms.

## Storage is not encrypted (recorded 2026-10-19)

Memory is stored as plaintext. A key stored beside its own ciphertext protects
against nothing, and reporting `cryptographic` for such a setup would be the
blanket claim this document forbids.

Privacy here is a **retrieval** control instead:

- `save`/`observe`/`summarize` take `sensitivity`, validated against
  `resource_lineage.SENSITIVITIES`. An unknown label **raises**; it is never
  downgraded.
- `recall` and `profile` return only `public` and `internal` by default.
  Opt in with `allowed_sensitivities=SENSITIVITIES`. An empty set means
  **nothing** is returned, not everything.
- `get(id)` is ungated on purpose: knowing the id means you already have it.
- The filter runs before `_strengthen`, so a suppressed match cannot bump a
  counter someone else can read back.

What `sensitive` does not do: encrypt the bytes. For that, `CellCipher` with the
key stored outside the data directory, or full-disk encryption. Different tools
for different threats.

**Rule:** never let `erasure_class` say `cryptographic` unless cells were
actually sealed. Both `forget.cipher_capability` and
`CellCipher.capability()` keep `cipher_class` (can it?) separate from
`erasure_class` (did it?), and an empty key store is always access control.

## Integration sources (repos read, patterns ported)

- deja-vu (Go), harness-books, claude-code-book, wshobson/agents, qm (TypeScript),
  AI-Builder-Club/skills. Research copies live in `../_research_2026-08/`.
  Ported modules are clean-room reimplementations, never vendored code.
  See `docs/SESSION_INDEX_AND_GOVERNANCE.md` and `docs/third_party_provenance.json`.
- harness2 (Google, Apache-2.0, arXiv 2610.14224), added 2026-10-19: cue/lesson/
  evidence triple, per-domain adopted-artifact libraries, anonymised selection,
  before/after contrast, run-identity budget ledger. Port notes:
  `docs/HARNESS2_PORT_NOTES.md`.

## Known gap: forgetting (recorded 2026-10-19)

The field moved while this repo was idle. Four recent results:

- **Bemula** (arXiv 2610.18052): no evaluated memory system passes more than
  1.5% of forget requests end to end.
- **MemCut** (2610.21405): deleting a narrow selection leaves 39-76% residual
  recovery; broad cut beats precise selection.
- **Deployment-Time Memorization** (2606.10062): derived copies stay
  recoverable in ~20% of cases; only a full-pipeline purge or tombstone
  reaches zero residue.
- **SAIHM** (IETF draft, 2026-10-11): erasure needs a receipt in a public log
  and a public list of erased ids.

So forgetting is a *measured* property, not a claim. `forget.py` must be able
to report what is still extractable after erasure, and `benchmarks/forget20.py`
must fail when it cannot.

**Status after round 2 (2026-10-19):** eight stores are covered (memory,
observations, summaries, graph, lessons, skills, library, promotion); SQLite is
hardened (`secure_delete`, WAL truncate, `VACUUM`) and raw bytes are scanned
after every erasure. One earlier claim was **wrong and is corrected**:
`LearningPromotionState` holds only `*_digest` fields, so it never carried
content.

**Cryptographic erasure (2026-10-19, round 3):** `aead.py` implements
ChaCha20-Poly1305 from RFC 8439 and checks itself against all 11 published test
vectors; `cell_cipher.py` seals each cell under its own key and erases by
destroying that key. `cipher_capability()` reports the *cryptographic* class
only after those vectors pass on the running interpreter.

Rules that follow from it:

- Never add a second cipher implementation. One verified implementation is
  auditable; two are not.
- Never reuse a key across cells. One key per cell is what makes one
  destruction reach exactly one cell.
- Never describe a store as cryptographically erased unless it was actually
  sealed. A store that only swept rows is access-control erased, and the
  receipt must say so.
- A copied key defeats key destruction. That is a deployment duty (SAIHM: destroy
  every copy including backups and replicas), not something this library can
  do. Declare backup roots so a receipt cannot imply otherwise.
