# Research digest — 2026-10-19 forgetting round

This note lives in the repository because the external research directory
(`../_research_2026-08/`) is on a removable drive that is not always mounted.
Provenance must survive an unmounted disk.

## What was read, and what came of it

| Work | Identifier | Finding that drove work here |
|---|---|---|
| **Bemula** | arXiv 2610.18052 | First memory-unlearning benchmark. No evaluated system passes more than 1.5% of forget requests end to end. Cause: one fact in several derived forms, so deleting one copy leaves the rest. |
| **MemCut** | arXiv 2610.21405 | *Native recovery* and *residual recovery* are different numbers; narrow deletion leaves 39-76% residue. Coverage, not selection accuracy, is the bottleneck. Minimal evidence combinations per secret are annotated in their corpus. |
| **Deployment-Time Memorization** | arXiv 2606.10062 | Forgetting Residue Score. Raw-only deletion leaves derived copies recoverable in about 20% of cases; only a full-pipeline purge or cryptographic erasure reaches zero. |
| **SAIHM** | IETF draft-saihm-memory-protocol-03, 2026-10-11 | Two erasure classes, *cryptographic* and *access-control*; an operator MUST state which and MUST NOT describe the second as the first. Erasure writes a receipt and a public erasure list. |
| **Agent-Controlled Forgetting** | arXiv 2610.10590 | Eviction from the active context is not deletion. Kept out of scope deliberately: it is a token-economy technique, not an erasure claim. |
| **AutoMEM** | arXiv 2606.04315 | An agent harness that self-manages memory beats passive stores across scenarios. Supports this project's split: deterministic core, agent on top. |
| **Anatomy of Agentic Memory** | arXiv 2602.19320 | Benchmarks are underscaled and metrics misaligned; system cost is usually ignored. Read as a warning about over-claiming from small benches. |
| **Harness2** | arXiv 2610.14224, Apache-2.0 | Cue/lesson/evidence triple, per-domain libraries, anonymised selection, before/after contrast, run-identity ledger. Ported earlier the same day; see `HARNESS2_PORT_NOTES.md`. |

## What was implemented as a result

1. `forget.py` — erasure by predicate across eight stores, receipts, residue
   reporting (native and residual), SQLite hardening, raw-byte scanning,
   sidecar scrubbing, fsync durability, backup declaration.
2. `aead.py` — ChaCha20-Poly1305 from **RFC 8439**, verified against all 11
   published vectors including Appendix A.3.
3. `cell_cipher.py` — per-cell keys; erasure by key destruction, which is the
   cryptographic class SAIHM defines.
4. `benchmarks/forget20.py` — 20 plant-and-forget cases plus four MemCut-shaped
   evidence-trail scenarios.

## The two claims that changed, and why that matters

This round corrected two earlier statements rather than quietly dropping them.

**Wrong, now fixed:** the first note said a secret could be sitting in
`LearningPromotionState`. Measuring the schema showed every record field is a
`*_digest`; the store never carried content. The property is now asserted by a
test instead of remembered.

**Reversed, now stronger:** the first note said cryptographic erasure was
impossible under the zero-dependency rule. That was true of the *stdlib alone*
but not of the rule: writing a cipher is allowed, vendoring one is not. With
RFC 8439 implemented and verified, the cryptographic class is reachable. The
old claim was not wrong about Python — it was wrong about what to do next.

## What this round still does not claim

- A **copied key** defeats key destruction. SAIHM puts the duty on the
  deployment to destroy every copy, including backups and replicas.
- **Raw storage blocks** are unreachable from user space. Full-disk encryption
  plus key destruction is the answer at that layer, not this library.
- **CPython is not constant-time.** The algorithm has no data-dependent
  branches; the interpreter does. Fine for at-rest local memory, not for a
  network protocol facing a timing attacker.
- The **bench is synthetic**, with four shapes. A regression gate, not a
  benchmark result.