# Learning Corpus Binding

Normative contract for the Gate 1 evidence-corpus provenance binding in [`noesis_harness/learning_corpus_binding.py`](../noesis_harness/learning_corpus_binding.py): a tamper-evident, deterministic envelope that pins a promotion proposal to an `evaluate_corpus_v2` report digest before the proposal can carry evidence claims on operator surfaces.

## Purpose

Review proposals must carry evidence-corpus provenance that can be verified independently of the proposer. The binding is an integrity envelope over canonical JSON: it records which corpus report (by schema version and digest) a promotion proposal is bound to, and it fails closed on any tampering, shape violation, or report mismatch. The deterministic core rule holds: no wall clock is read unless the caller injects one; bindings without an injected clock are byte-stable across runs and machines.

## Binding schema

`bind_corpus_evidence` returns a dict with exactly these keys (`bound_at_unix` and `max_age_seconds` are optional; everything else required):

| Key | Content | Pinned by |
|---|---|---|
| `schema_version` | Always `noesis.learning-corpus-binding.v1`. | Module constant. |
| `corpus_schema_version` | Must equal the v2 corpus schema (`noesis.memory-quality-corpus.v2`). | Validated against the corpus module constant. |
| `corpus_report_digest` | `sha256:` + 64 hex chars from the corpus report's `report_digest`. | Shape-validated, cross-checked on verify when the report is supplied. |
| `subject.kind` | Always `promotion_proposal`. | Closed vocabulary. |
| `subject.proposal_id` | `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}` safe id. | Regex-validated fail-closed. |
| `subject.skill_digest` | The proposal's content digest, recorded under a redaction-safe key name. | Length-capped string. |
| `subject.provenance_digest` | The proposal's provenance digest. | Length-capped string. |
| `bound_at_unix` | Present only when a clock is injected. | Must be finite and non-negative. |
| `max_age_seconds` | Freshness policy; requires `bound_at_unix`. | Must be finite and positive. |
| `binding_digest` | sha256 over the canonical binding without this key. | Recomputed and compared with `hmac.compare_digest`. |

## Module contract

- `bind_corpus_evidence(proposal_builder_or_proposal, corpus_report, *, max_age_seconds=None, clock=None)` accepts a `PromotionProposal`, any dataclass or mapping carrying `proposal_id`, `content_digest`, and `provenance_digest`, or a zero-arg callable returning either. Builder exceptions surface as `subject_builder_failed`, never silently.
- Default output is timestamp-free and byte-stable: `bound_at_unix` exists only when `clock` is injected; `max_age_seconds` requires a clock (`clock_required_for_max_age`), so a freshness policy can never be forged onto a timeless binding.
- `verify_corpus_binding(binding, *, corpus_report=None)` is fail-closed and never raises: closed key vocabulary (unknown extra keys reject even if the attacker rebuilds the digest), schema checks, subject shape checks, integrity digest over canonical JSON via `hmac.compare_digest`, and an optional mismatch check against a supplied corpus report.
- `attach_to_telemetry(telemetry_payload, binding)` attaches only a verified binding under `corpus_binding`; idempotency conflict policy is fail-closed — an existing key raises `telemetry_binding_conflict` instead of being overwritten.
- Subject key names are deliberately redaction-safe: `PromotionTelemetry._redact` masks any key containing "content", so the canonical `content_digest` field is recorded as `skill_digest`, keeping the binding verbatim-verifiable after telemetry redaction.
- [`noesis_harness/promotion_integration.py`](../noesis_harness/promotion_integration.py) `PromotionIntegration.propose` accepts an optional keyword-only `corpus_binding`: it verifies the binding fail-closed BEFORE the pipeline side effect, then attaches it additively to the `promotion_proposed` telemetry event.

## Typed values and error codes

`LearningCorpusBindingError` codes: `corpus_report_invalid`, `subject_invalid`, `subject_builder_failed`, `subject_proposal_id_invalid`, `subject_digests_invalid`, `clock_not_callable`, `clock_value_invalid`, `max_age_seconds_invalid`, `clock_required_for_max_age`, `telemetry_payload_invalid`, `telemetry_binding_conflict`, `binding_verification_failed`.

Schema constants: `BINDING_SCHEMA_VERSION = noesis.learning-corpus-binding.v1`; telemetry key `TELEMETRY_BINDING_KEY = corpus_binding`. Verification is boolean; builders raise typed errors.

## Wiring status

Integrated keyword-only into `PromotionIntegration.propose` in [`noesis_harness/promotion_integration.py`](../noesis_harness/promotion_integration.py): an invalid binding aborts propose before any pipeline state changes; a valid binding rides the `promotion_proposed` telemetry payload under `corpus_binding` and survives redaction verbatim.

## Related tests

- [`tests/test_learning_corpus_binding.py`](../tests/test_learning_corpus_binding.py) — round-trip bind/verify against a real v2 corpus report, builder/mapping/direct subject equivalence, invalid-input fail-closed set, determinism with and without injected clocks, tamper detection (digest, payload fields, foreign reports, forged extra keys), telemetry attach conflict policy, and `PromotionIntegration.propose` integration including pre-side-effect failure.

## Provenance

Patterns borrowed per repo discipline: agentmemory governance receipt patterns — tamper-evident canonical JSON + sha256 integrity envelope with fail-closed verification (`hmac.compare_digest`) as already ported in learning_promotion/promotion_integration; deepseek-harness fail-closed verification discipline mirrored in `memory_quality_corpora.verify_case_provenance`. No LLM, no network, no wall clock unless injected.

## Claim boundary

A verified binding attests only that the named proposal was associated with a corpus report having the pinned digest at bind time, and that the envelope has not been altered since. It does not attest external model quality, re-run the corpus, or validate the skill content itself; freshness enforcement via `max_age_seconds` is the verifier's responsibility.
