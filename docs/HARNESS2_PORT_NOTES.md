# Harness2 port notes

**Source:** https://github.com/AMAImedia/harness2 — Harness², *Recursive Agent
Harnessing for an Open World*, arXiv 2610.14224 (Xu, Chen, CuiZhu, Dalvi Mishra,
Ming, Yu, Han, Lee, Pfister). Apache-2.0. Open-source release by Google; not an
officially supported Google product. Research copy lives at
`../_research_2026-08/harness2`.

**Status of this port:** clean-room. No Harness2 source line was copied. Only
data contracts and methods were reimplemented against this project's rules
(`AGENTS.md`): stdlib only, deterministic core with the LLM optional,
append-only state, idempotency on every write path, no file deletion.

Recorded in `third_party_provenance.json` under `harness2`.

---

## 1. What Harness2 is, in one paragraph

The *harness* is everything around a model that turns it into an agent:
system prompt, guardrails, memory, skills, scripts, plugins, subagents, tool
guidance. Harness2 optimises the harness itself, and a second agent does the
optimising. Two loops are connected: a task-level loop that refines the harness
for one task through a contrastive Propose-Probe-Compose step with no
ground-truth feedback, and a harnessing-level loop that stores the adopted
harness plus evidence-supported lessons in a per-domain library for later
tasks.

## 2. Their reported results, and the condition attached

Across three professional benchmarks and four model-harness configurations, one
Harness² step improves GLM-5 and Gemini 3.5 Flash over their base harnesses:
up to 11.5 points on WorkBuddy-Bench, 4.5 on JobBench, and 11.8 percentage
points on LAB partial pass rate. Increasing the task-level recursion budget
buys further gains.

Two conditions must travel with those numbers whenever they are quoted:

1. In a validation run of their own release, a Codex rollout on JobBench
   downloaded the task's own `RUBRUBS.json` from Hugging Face without being
   told to. Their release does not restrict executor network access, and they
   say so and recommend an egress firewall.
2. `k` in their tables is the recursion budget, and the cost scales linearly
   with it: `R = 4k` rollouts and `P = 3k` improvement stages per task.

Neither condition weakens the result. Both change what kind of claim it is.

## 3. The gap analysis that drove this port

Before this work, NOESIS had two halves that were not connected to each other:

- **Governed promotion** (`learning_promotion`, `promotion_integration`): a
  fully governed lifecycle with all-or-nothing holdouts, HMAC signatures, an
  independent reviewer, operator sessions and a two-phase activation journal.
  No LLM anywhere. Nothing ever auto-promotes.
- **Retrieval and measurement** (`memory`, `memory_quality`, `memory_ab`):
  deterministic BM25/FTS5/vector-RRF recall with decay, plus offline evaluators
  that score recorded traces.

Three structural gaps followed from that:

| Gap | Evidence before the port |
|---|---|
| No cue-addressed lesson type | zero occurrences of `cue` or `lesson` in `noesis_harness/` |
| No per-domain scoping | `scope` meant agent/session/organisation; "domain of work" existed only in report formatting |
| The two halves never met | `ExperienceReuseSelector` had no production caller; nothing wrote an `ExperienceRecord` from an `ExperienceReceipt` |

## 4. What was ported

### 4.1 `lesson_cue.py` — the cue / lesson / evidence triple

Harness2's `core/library.py` stores an `EXPERIENCE.md` whose reusable part is a
three-part record, and their `core/selection.py::_distil` refuses to store a
lesson unless all three parts are present. That contract was the missing piece:
NOESIS could promote a skill *version* under approval but had no data type for
"something a past task learned that a future task can recall by its situation".

Ported as `Lesson(lesson_id, cue, lesson, evidence, domain, confidence, scope,
sensitivity, source_ids, status, ...)`, plus:

- `CueSelector` — bounded, scoped, deny-by-default, deterministic recall;
- `LessonJournal` — append-only JSONL, content-addressed idempotency;
- `extract_lesson(task, extractor)` — the extractor is a callback, so the
  deterministic core never calls a model.

The cue match reuses this project's own `inverted_index.STOPWORDS` and the
three-character cutoff from `procedures.py`, so the whole project tokenises one
way.

### 4.2 `domain_library.py` — per-domain libraries of adopted artifacts

Their layout (`<root>/<domain>/INDEX.md`, full trees carried rather than
summarised, retrieval by construction) and their `retain` prefix rule. See
section 5 for the governance difference.

### 4.3 `blind_select.py` — anonymised selection and the before/after contrast

Their `assign_ids` (canonical sort, then a seeded shuffle), their `A..Z`/`AA`
identifier walk, the recorded `id_map` that de-anonymises stored reasoning after
the fact, the neutral fallback on chooser failure, and the `difflib` contrast
per candidate.

### 4.4 `budget.py` — the run-identity ledger

`Budget` already answered "how many units may this day spend". It did not
answer "did this run do what it said it would do": two stages writing the same
label means one silently overwrote the other, and the count still adds up.
`RunLedger` adds `expected_rollouts(k) = 4k`, `expected_sessions(k) = 3k`, and
`assert_identity()` which checks duplicates *before* counts — because a
duplicate can satisfy the counts.

## 5. Where this port is deliberately stricter than the source

This matters more than the list of what was taken.

| Behaviour | Harness2 | Here, and why |
|---|---|---|
| Writing to the library | the reflection step writes directly | `LibraryEntry` requires `approved_by`; a lesson stays a candidate until `LessonJournal.promote` with a named actor |
| Selection outcome | adopted | `Selection.is_adopted` is False for any fallback or trivial result, so a pipeline must ask for a real judgement rather than a neutral stand-in |
| Re-evaluating a lesson | not applicable | `supersede` appends a successor; the log is never rewritten |
| Determinism of ordering | per-mode | one agreed order (`seq`, then `task_id`) shared by `task_ids`, `entries` and `retain` |

## 6. What was deliberately not ported

- **The LLM harness editor.** It would make the core depend on a model, which
  this project's rules forbid. Only the data contract came across; extraction
  is a callback.
- **The recursion machinery itself** (`Propose-Probe-Compose`, parallel vs
  sequential `k`). NOESIS is a memory harness, not a harness optimiser. The
  adopted-experience half is what belongs here.
- **Third-party benchmark runners, patches and data.** Not needed for memory,
  and WorkBuddy's upstream license carries a territorial limitation concerning
  use within the European Union.
- **Judge-failure-as-None.** Already present here via `memory_quality`; nothing
  to duplicate.
- **`runmark` fingerprint gating.** Worth doing, but it is a distinct change to
  execution resume and was left out of this batch.

## 7. Defects the new tests caught in the new code

Worth recording, because all four were real and none would have been visible
without writing the test first.

1. **`domain_dir("..")` escaped the library root.** Separator collapsing stops
   `../x`, but a domain label that is itself `..` needs no separator:
   `root / ".."` is the parent directory. Now escaped.
2. **Two views of a library disagreed on order.** `task_ids()` used `seq` while
   `entries()` sorted by `created_at`, so `retain` could compute a prefix that
   `entries` printed differently. Now one agreed order.
3. **`build_contrast` raised `NameError`** on any removed artifact — a wrong
   comprehension variable.
4. **`assign_ids` silently collapsed duplicate labels.** The duplicate check
   compared a de-duplicated set against itself, so it could never fire.

Two more were found and fixed before their tests: a cue's exact tier was
unreachable through prose stopwords, and a distance-0 token match was being
reported as a fuzzy hit, which made the fuzzy tier reachable by an exact match
and hid the real state of the cue.

## 8. Test coverage added

| File | Tests |
|---|---|
| `tests/test_lesson_cue.py` | 39 |
| `tests/test_domain_library.py` | 29 |
| `tests/test_blind_select.py` | 34 |
| `tests/test_run_ledger.py` | 16 |

## 9. Pre-existing failures, not caused by this work

Before this change the suite already reported `Ran 2267 tests ... failures=5,
errors=1`. All six are Windows-specific and unrelated to memory:

- `test_appcontainer_backend` (4)
- `test_native_artifact_evidence` (1)
- `test_verify_operator_artifact_cli` (1)

One behaviour found while writing `tests/test_run_ledger.py` and left
unchanged, because changing it is a separate decision: `Budget.spend` checks
the daily cap *before* recognising an already-counted key, so once the day is
exhausted a re-spend of a counted key is refused rather than reported as a
no-op. It is recorded as `test_the_cap_is_checked_before_the_key_is_recognised`
so that any future change to it is deliberate.