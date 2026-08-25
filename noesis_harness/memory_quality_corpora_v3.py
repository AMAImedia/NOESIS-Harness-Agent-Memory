"""Adversarial memory-quality corpora v3 (Gate 1 broader independent corpora).

Second corpus family produced by an independent seeded procedure rather than
hand-pinned constants. Every identifier, vocabulary word, numeric edge, and
flag polarity is drawn from an explicit linear congruential generator over
small finite tables: the LCG stream is ported from work_product_ma08_ma09.py
(32-bit state, high-bit draws avoid short cycles). Identical seeds therefore
reproduce byte-identical corpora while different seeds structurally differ;
both properties are asserted fail-closed inside the generator. Case shape and
scoring follow the recorded-trajectory pattern of the agentmemory quality-trace
lineage (scripts/run_memory_quality_evidence.py) with fail-closed expectation
checks in the spirit of deepseek-harness adversarial suites. The untouched core
MemoryQualityEvaluator remains the only scorer: no wall clock, no random module.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from .memory import Memory
from .memory_quality import MemoryQualityCase, MemoryQualityEvaluator, MemoryTrajectoryStep


CORPUS_SCHEMA_VERSION_V3 = "noesis.memory-quality-corpus.v3"
DEFAULT_SEED_V3 = 8675309
DEFAULT_CASES_PER_CATEGORY_V3 = 2
MAX_CASES_PER_CATEGORY_V3 = 16
BUDGET_MIN_V3 = 48
BUDGET_SPAN_V3 = 33
TRACE_LEN_MIN_V3 = 6
TRACE_LEN_SPAN_V3 = 5
DECAY_PERIOD_CHOICES_V3 = (1, 2)
DECAY_SUBFLOOR_MULTIPLIERS_V3 = (0.5, 0.75)
DUP_COUNT_CHOICES_V3 = (2, 3)
ATTR_NOISE_COUNT_CHOICES_V3 = (1, 2)

CATEGORIES_V3: Tuple[str, ...] = (
    "temporal_inversion_pair",
    "duplicate_attribution",
    "near_duplicate_query",
    "budget_edge_long_trace",
    "conflict_with_provenance",
    "decay_floor_boundary",
    "leakage_decoy",
    "cross_session_decoy_reuse",
)

_CATEGORY_ABBREV_V3: Mapping[str, str] = {
    "temporal_inversion_pair": "tmpinv",
    "duplicate_attribution": "dupatt",
    "near_duplicate_query": "neardup",
    "budget_edge_long_trace": "budgedg",
    "conflict_with_provenance": "confprv",
    "decay_floor_boundary": "decflr",
    "leakage_decoy": "leakdec",
    "cross_session_decoy_reuse": "xsdecoy",
}

_CATEGORY_FLAVOR_V3: Mapping[str, str] = {
    "temporal_inversion_pair": "ordering",
    "duplicate_attribution": "isolation",
    "near_duplicate_query": "checkpoint",
    "budget_edge_long_trace": "packing",
    "conflict_with_provenance": "lease",
    "decay_floor_boundary": "retention",
    "leakage_decoy": "probe",
    "cross_session_decoy_reuse": "restore",
}

_VOCAB_ACTIONS_V3: Tuple[str, ...] = ("audit", "resume", "rollback", "verify", "replay", "compact")
_VOCAB_OBJECTS_V3: Tuple[str, ...] = ("receipt", "manifest", "ledger", "cursor", "snapshot", "dossier")
_VOCAB_STATES_V3: Tuple[str, ...] = ("stale", "current", "signed", "sealed", "durable", "volatile")


class MemoryQualityCorpusError(ValueError):
    """Raised when the corpus definition, parameters, or an adapter violate the contract."""


@dataclass(frozen=True)
class AdversarialCorpusCaseV3:
    """One generated adversarial case mapped onto untouched evaluator inputs."""

    case_id: str
    category: str
    session_id: str
    query: str
    relevant_source_ids: Tuple[str, ...]
    selected_source_ids: Tuple[str, ...]
    attributed_source_ids: Tuple[str, ...]
    conflict_resolution_correct: bool
    temporal_order_correct: bool
    retained_after_compaction_ids: Tuple[str, ...]
    required_after_compaction_ids: Tuple[str, ...]
    used_tokens: int
    budget_tokens: int
    leakage_free: bool = True
    reused_experience_ids: Tuple[str, ...] = ()
    relevant_experience_ids: Tuple[str, ...] = ()
    decay_base_strengths: Tuple[float, ...] = ()
    decay_periods: int = 0

    def payload(self) -> Dict[str, Any]:
        return {
            "attributed_source_ids": list(self.attributed_source_ids),
            "budget_tokens": int(self.budget_tokens),
            "case_id": self.case_id,
            "category": self.category,
            "conflict_resolution_correct": bool(self.conflict_resolution_correct),
            "decay_base_strengths": list(self.decay_base_strengths),
            "decay_periods": int(self.decay_periods),
            "leakage_free": bool(self.leakage_free),
            "query": self.query,
            "relevant_experience_ids": list(self.relevant_experience_ids),
            "relevant_source_ids": list(self.relevant_source_ids),
            "required_after_compaction_ids": list(self.required_after_compaction_ids),
            "retained_after_compaction_ids": list(self.retained_after_compaction_ids),
            "reused_experience_ids": list(self.reused_experience_ids),
            "selected_source_ids": list(self.selected_source_ids),
            "session_id": self.session_id,
            "temporal_order_correct": bool(self.temporal_order_correct),
            "used_tokens": int(self.used_tokens),
        }

    def provenance_digest(self) -> str:
        encoded = json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def to_memory_quality_case(self) -> MemoryQualityCase:
        return MemoryQualityCase(
            self.case_id,
            self.relevant_source_ids,
            self.selected_source_ids,
            self.attributed_source_ids,
            self.conflict_resolution_correct,
            self.temporal_order_correct,
            self.retained_after_compaction_ids,
            self.required_after_compaction_ids,
            self.used_tokens,
            self.budget_tokens,
            self.leakage_free,
            self.reused_experience_ids,
            self.relevant_experience_ids,
        )

    def to_trajectory_step(self) -> MemoryTrajectoryStep:
        return MemoryTrajectoryStep(
            self.case_id,
            self.query,
            self.relevant_source_ids,
            self.selected_source_ids,
            self.attributed_source_ids,
            self.reused_experience_ids,
            self.relevant_experience_ids,
            self.conflict_resolution_correct,
            self.temporal_order_correct,
            self.retained_after_compaction_ids,
            self.required_after_compaction_ids,
            self.used_tokens,
            self.budget_tokens,
            self.leakage_free,
        )


class _LcgRandom:
    """Deterministic LCG ported from work_product_ma08_ma09 (high bits avoid short cycles)."""

    def __init__(self, seed: int) -> None:
        self._state = int(seed) & 0xFFFFFFFF

    def next_draw(self) -> int:
        self._state = (self._state * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._state >> 16) & 0x7FFF

    def below(self, bound: int) -> int:
        if int(bound) < 1:
            raise MemoryQualityCorpusError("lcg_bound_invalid")
        return self.next_draw() % int(bound)

    def pick(self, options: Sequence[str]) -> str:
        return options[self.below(len(options))]

    def hex4(self) -> str:
        return "%04x" % self.next_draw()

    def distinct_hex4(self, forbidden: str) -> str:
        for _ in range(64):
            candidate = self.hex4()
            if candidate != forbidden:
                return candidate
        raise MemoryQualityCorpusError("lcg_draw_space_exhausted")


class _GenerationContextV3:
    def __init__(self, rng: _LcgRandom, seed: int) -> None:
        self.rng = rng
        self.seed_token = str(int(seed))
        self.prefix = "v3-c%s" % self.seed_token
        self.session_alpha = "%s-session-alpha" % self.prefix
        self.session_beta = "%s-session-beta" % self.prefix
        self.budget_tokens = BUDGET_MIN_V3 + rng.below(BUDGET_SPAN_V3)
        self.taken: set = set()

    def mint(self, kind: str) -> str:
        for _ in range(64):
            candidate = "%s-%s-%s" % (self.prefix, kind, self.rng.hex4())
            if candidate not in self.taken:
                self.taken.add(candidate)
                return candidate
        raise MemoryQualityCorpusError("source_id_space_exhausted")

    def trace_ids(self, abbrev: str, count: int) -> Tuple[str, ...]:
        traces = []
        for index in range(int(count)):
            candidate = "%s-%s-trace-%02d-%s" % (self.prefix, abbrev, index, self.rng.hex4())
            while candidate in self.taken:
                candidate = candidate + "-" + self.rng.hex4()
            self.taken.add(candidate)
            traces.append(candidate)
        return tuple(traces)

    def query(self, category: str, extra: str = "") -> str:
        words = (
            _CATEGORY_FLAVOR_V3[category],
            self.rng.pick(_VOCAB_ACTIONS_V3),
            self.rng.pick(_VOCAB_OBJECTS_V3),
            self.rng.pick(_VOCAB_STATES_V3),
        )
        parts = list(words) + ["token", str(self.rng.next_draw() % 97)]
        if extra:
            parts.append(extra)
        return " ".join(parts)


def _assemble_v3(
    case_id: str,
    category: str,
    session_id: str,
    query: str,
    relevant: Tuple[str, ...],
    selected: Tuple[str, ...],
    attributed: Tuple[str, ...],
    conflict_ok: bool,
    temporal_ok: bool,
    retained: Tuple[str, ...],
    required: Tuple[str, ...],
    used_tokens: int,
    budget_tokens: int,
    *,
    leakage_free: bool = True,
    reused_experience_ids: Tuple[str, ...] = (),
    relevant_experience_ids: Tuple[str, ...] = (),
    decay_base_strengths: Tuple[float, ...] = (),
    decay_periods: int = 0,
) -> AdversarialCorpusCaseV3:
    return AdversarialCorpusCaseV3(
        case_id,
        category,
        session_id,
        query,
        relevant,
        selected,
        attributed,
        conflict_ok,
        temporal_ok,
        retained,
        required,
        used_tokens,
        budget_tokens,
        leakage_free,
        reused_experience_ids,
        relevant_experience_ids,
        decay_base_strengths,
        decay_periods,
    )


def _build_temporal_inversion_pair(rng: _LcgRandom, ctx: _GenerationContextV3, count: int) -> List[AdversarialCorpusCaseV3]:
    cases = []
    for index in range(count):
        temporal_ok = index % 2 == 0
        source = ctx.mint(_CATEGORY_ABBREV_V3["temporal_inversion_pair"] + "-src")
        cases.append(
            _assemble_v3(
                "%s-tmpinv-%02d" % (ctx.prefix, index + 1),
                "temporal_inversion_pair",
                ctx.session_alpha,
                ctx.query("temporal_inversion_pair"),
                (source,),
                (source,),
                (source,),
                True,
                temporal_ok,
                (source,),
                (source,),
                12 + rng.below(9),
                ctx.budget_tokens,
            )
        )
    return cases


def _build_duplicate_attribution(rng: _LcgRandom, ctx: _GenerationContextV3, count: int) -> List[AdversarialCorpusCaseV3]:
    cases = []
    for index in range(count):
        dup_count = DUP_COUNT_CHOICES_V3[rng.below(len(DUP_COUNT_CHOICES_V3))]
        noise_count = ATTR_NOISE_COUNT_CHOICES_V3[rng.below(len(ATTR_NOISE_COUNT_CHOICES_V3))]
        abbrev = _CATEGORY_ABBREV_V3["duplicate_attribution"]
        primary = ctx.mint(abbrev + "-src")
        noises = tuple(ctx.mint(abbrev + "-noise") for _ in range(noise_count))
        cases.append(
            _assemble_v3(
                "%s-dupatt-%02d" % (ctx.prefix, index + 1),
                "duplicate_attribution",
                ctx.session_alpha,
                ctx.query("duplicate_attribution"),
                (primary,),
                (primary,) + noises,
                (primary,) * dup_count + noises,
                True,
                True,
                (primary,),
                (primary,),
                14 + rng.below(9),
                ctx.budget_tokens,
            )
        )
    return cases


def _build_near_duplicate_query(rng: _LcgRandom, ctx: _GenerationContextV3, count: int) -> List[AdversarialCorpusCaseV3]:
    cases = []
    for index in range(count):
        abbrev = _CATEGORY_ABBREV_V3["near_duplicate_query"]
        own = ctx.mint(abbrev + "-src")
        other = ctx.mint(abbrev + "-variant")
        token_own = rng.hex4()
        token_other = rng.distinct_hex4(token_own)
        cases.append(
            _assemble_v3(
                "%s-neardup-%02d" % (ctx.prefix, index + 1),
                "near_duplicate_query",
                ctx.session_alpha,
                ctx.query("near_duplicate_query", extra="checkpoint %s %s" % (token_own, token_other)),
                (own,),
                (own, other),
                (own,),
                True,
                True,
                (own,),
                (own,),
                18 + rng.below(9),
                ctx.budget_tokens,
            )
        )
    return cases


def _build_budget_edge_long_trace(rng: _LcgRandom, ctx: _GenerationContextV3, count: int) -> List[AdversarialCorpusCaseV3]:
    cases = []
    for index in range(count):
        overrun = index % 2 == 1
        abbrev = _CATEGORY_ABBREV_V3["budget_edge_long_trace"]
        relevant = ctx.mint(abbrev + "-src")
        traces = ctx.trace_ids(abbrev, TRACE_LEN_MIN_V3 + rng.below(TRACE_LEN_SPAN_V3))
        cases.append(
            _assemble_v3(
                "%s-budgedg-%02d" % (ctx.prefix, index + 1),
                "budget_edge_long_trace",
                ctx.session_alpha,
                ctx.query("budget_edge_long_trace"),
                (relevant,),
                (relevant,) + traces,
                (relevant,),
                True,
                True,
                (relevant,),
                (relevant,),
                ctx.budget_tokens + (1 if overrun else 0),
                ctx.budget_tokens,
            )
        )
    return cases


def _build_conflict_with_provenance(rng: _LcgRandom, ctx: _GenerationContextV3, count: int) -> List[AdversarialCorpusCaseV3]:
    cases = []
    for index in range(count):
        conflict_ok = index % 2 == 1
        abbrev = _CATEGORY_ABBREV_V3["conflict_with_provenance"]
        current = ctx.mint(abbrev + "-current")
        stale = ctx.mint(abbrev + "-stale")
        cases.append(
            _assemble_v3(
                "%s-confprv-%02d" % (ctx.prefix, index + 1),
                "conflict_with_provenance",
                ctx.session_alpha,
                ctx.query("conflict_with_provenance"),
                (current,),
                (stale, current),
                (current,),
                conflict_ok,
                True,
                (current,),
                (current,),
                21 + rng.below(9),
                ctx.budget_tokens,
            )
        )
    return cases


def _build_decay_floor_boundary(rng: _LcgRandom, ctx: _GenerationContextV3, count: int) -> List[AdversarialCorpusCaseV3]:
    cases = []
    floor = float(Memory.DECAY_FLOOR)
    for index in range(count):
        periods = DECAY_PERIOD_CHOICES_V3[rng.below(len(DECAY_PERIOD_CHOICES_V3))]
        multiplier = DECAY_SUBFLOOR_MULTIPLIERS_V3[rng.below(len(DECAY_SUBFLOOR_MULTIPLIERS_V3))]
        base_at_floor = floor * float(2 ** periods)
        base_subfloor = base_at_floor * multiplier
        if not (base_at_floor * (0.5 ** periods)) == floor or not (base_subfloor * (0.5 ** periods)) < floor:
            raise MemoryQualityCorpusError("decay_fixture_invalid")
        abbrev = _CATEGORY_ABBREV_V3["decay_floor_boundary"]
        floor_id = ctx.mint(abbrev + "-floor")
        subfloor_id = ctx.mint(abbrev + "-subfloor")
        cases.append(
            _assemble_v3(
                "%s-decflr-%02d" % (ctx.prefix, index + 1),
                "decay_floor_boundary",
                ctx.session_alpha,
                ctx.query("decay_floor_boundary"),
                (floor_id,),
                (floor_id,),
                (floor_id,),
                True,
                True,
                (floor_id,),
                (floor_id, subfloor_id),
                13 + rng.below(9),
                ctx.budget_tokens,
                decay_base_strengths=(base_at_floor, base_subfloor),
                decay_periods=periods,
            )
        )
    return cases


def _build_leakage_decoy(rng: _LcgRandom, ctx: _GenerationContextV3, count: int) -> List[AdversarialCorpusCaseV3]:
    cases = []
    for index in range(count):
        leakage_free = index % 2 == 1
        abbrev = _CATEGORY_ABBREV_V3["leakage_decoy"]
        target = ctx.mint(abbrev + "-target")
        decoy = ctx.mint(abbrev + "-decoy")
        cases.append(
            _assemble_v3(
                "%s-leakdec-%02d" % (ctx.prefix, index + 1),
                "leakage_decoy",
                ctx.session_alpha,
                ctx.query("leakage_decoy"),
                (target,),
                (target, decoy),
                (target,),
                True,
                True,
                (target,),
                (target,),
                17 + rng.below(9),
                ctx.budget_tokens,
                leakage_free=leakage_free,
            )
        )
    return cases


def _build_cross_session_decoy_reuse(rng: _LcgRandom, ctx: _GenerationContextV3, count: int) -> List[AdversarialCorpusCaseV3]:
    real_experience = ctx.mint("xsdecoy-exp-real")
    decoy_experience = ctx.mint("xsdecoy-exp-decoy")
    cases = []
    for index in range(count):
        reuse_real = index % 2 == 0
        source = ctx.mint(_CATEGORY_ABBREV_V3["cross_session_decoy_reuse"] + "-src")
        cases.append(
            _assemble_v3(
                "%s-xsdecoy-%02d" % (ctx.prefix, index + 1),
                "cross_session_decoy_reuse",
                ctx.session_beta,
                ctx.query("cross_session_decoy_reuse"),
                (source,),
                (source,),
                (source,),
                True,
                True,
                (source,),
                (source,),
                15 + rng.below(9),
                ctx.budget_tokens,
                reused_experience_ids=(real_experience if reuse_real else decoy_experience,),
                relevant_experience_ids=(real_experience,),
            )
        )
    return cases


_CATEGORY_BUILDERS_V3: Mapping[str, Callable[[_LcgRandom, _GenerationContextV3, int], List[AdversarialCorpusCaseV3]]] = {
    "temporal_inversion_pair": _build_temporal_inversion_pair,
    "duplicate_attribution": _build_duplicate_attribution,
    "near_duplicate_query": _build_near_duplicate_query,
    "budget_edge_long_trace": _build_budget_edge_long_trace,
    "conflict_with_provenance": _build_conflict_with_provenance,
    "decay_floor_boundary": _build_decay_floor_boundary,
    "leakage_decoy": _build_leakage_decoy,
    "cross_session_decoy_reuse": _build_cross_session_decoy_reuse,
}


def _build_corpus_v3(seed: int, cases_per_category: int) -> Tuple[AdversarialCorpusCaseV3, ...]:
    rng = _LcgRandom(seed)
    ctx = _GenerationContextV3(rng, seed)
    cases: List[AdversarialCorpusCaseV3] = []
    for category in CATEGORIES_V3:
        cases.extend(_CATEGORY_BUILDERS_V3[category](rng, ctx, cases_per_category))
    return tuple(cases)


def _canonical_json(mapping: Mapping[str, Any]) -> str:
    return json.dumps(mapping, sort_keys=True, separators=(",", ":"))


def corpus_digest_v3(cases: Sequence[AdversarialCorpusCaseV3]) -> str:
    """Sha256 over the canonical corpus payload list (order preserved)."""
    encoded = json.dumps([case.payload() for case in cases], sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _validate_generation_parameters(seed: int, cases_per_category: int) -> None:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise MemoryQualityCorpusError("seed_invalid")
    if isinstance(cases_per_category, bool) or not isinstance(cases_per_category, int):
        raise MemoryQualityCorpusError("cases_per_category_invalid")
    if cases_per_category < 1 or cases_per_category > MAX_CASES_PER_CATEGORY_V3:
        raise MemoryQualityCorpusError("cases_per_category_out_of_range")


def generate_corpus_v3(seed: int = DEFAULT_SEED_V3, cases_per_category: int = DEFAULT_CASES_PER_CATEGORY_V3) -> Tuple[AdversarialCorpusCaseV3, ...]:
    """Generate the seeded adversarial corpus (LCG-only, byte-reproducible).

    Fail-closed internal probes: unique ids, exact size, same-seed payload
    equality, and cross-seed id/digest inequality. Any broken property aborts
    generation instead of emitting an unverifiable corpus.
    """
    _validate_generation_parameters(seed, cases_per_category)
    cases = _build_corpus_v3(seed, cases_per_category)
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise MemoryQualityCorpusError("duplicate_corpus_case_id")
    if len(cases) != len(CATEGORIES_V3) * cases_per_category:
        raise MemoryQualityCorpusError("corpus_size_invalid")
    if sorted({case.category for case in cases}) != sorted(CATEGORIES_V3):
        raise MemoryQualityCorpusError("corpus_category_set_invalid")
    replayed = _build_corpus_v3(seed, cases_per_category)
    if corpus_digest_v3(replayed) != corpus_digest_v3(cases):
        raise MemoryQualityCorpusError("same_seed_divergence_detected")
    shifted = _build_corpus_v3(seed + 1, cases_per_category)
    if corpus_digest_v3(shifted) == corpus_digest_v3(cases):
        raise MemoryQualityCorpusError("cross_seed_collision_detected")
    if {case.case_id for case in shifted} & set(ids):
        raise MemoryQualityCorpusError("cross_seed_id_collision_detected")
    return cases


def project_decay_strengths_v3(base_strengths: Sequence[float], periods: int) -> Tuple[float, ...]:
    """Deterministic exponential decay clamped at the Memory decay floor."""
    floor = float(Memory.DECAY_FLOOR)
    factor = 0.5 ** int(periods)
    return tuple(max(floor, float(base) * factor) for base in base_strengths)


def _ratio(numerator: int, denominator: int) -> float:
    return 1.0 if denominator == 0 else float(numerator) / float(denominator)


def expected_metrics_v3(case: AdversarialCorpusCaseV3) -> Dict[str, Any]:
    """Expectation table entry derived arithmetically from generator metadata."""
    relevant = set(case.relevant_source_ids)
    selected = set(case.selected_source_ids)
    attributed = set(case.attributed_source_ids)
    retained = set(case.retained_after_compaction_ids)
    required = set(case.required_after_compaction_ids)
    recall = _ratio(len(relevant & selected), len(relevant))
    attribution_precision = _ratio(len(attributed & relevant), len(attributed))
    if case.category == "temporal_inversion_pair":
        return {"recall": recall, "temporal_order": float(case.temporal_order_correct)}
    if case.category == "duplicate_attribution":
        return {"recall": recall, "attribution_precision": attribution_precision}
    if case.category == "near_duplicate_query":
        return {"recall": recall, "attribution_precision": attribution_precision}
    if case.category == "budget_edge_long_trace":
        return {"recall": recall, "budget_respected": bool(case.used_tokens <= case.budget_tokens)}
    if case.category == "conflict_with_provenance":
        return {"recall": recall, "conflict_resolution": float(case.conflict_resolution_correct), "provenance_verified": True}
    if case.category == "decay_floor_boundary":
        return {
            "recall": recall,
            "compaction_retention": _ratio(len(required & retained), len(required)),
            "decay_floor_boundary_respected": True,
        }
    if case.category == "leakage_decoy":
        return {"recall": recall, "leakage_free": bool(case.leakage_free), "attribution_precision": attribution_precision}
    if case.category == "cross_session_decoy_reuse":
        reuse_recall = _ratio(
            len(set(case.reused_experience_ids) & set(case.relevant_experience_ids)),
            len(set(case.relevant_experience_ids)),
        )
        return {"recall": recall, "experience_reuse_recall": reuse_recall}
    raise MemoryQualityCorpusError("category_unknown")


def _roundtrip_evaluator_payload_v3(case: AdversarialCorpusCaseV3) -> Dict[str, Any]:
    step = case.to_trajectory_step()
    return {
        "attributed_source_ids": list(step.attributed_source_ids),
        "budget_tokens": int(step.budget_tokens),
        "case_id": step.step_id,
        "category": case.category,
        "conflict_resolution_correct": bool(step.conflict_resolution_correct),
        "decay_base_strengths": list(case.decay_base_strengths),
        "decay_periods": int(case.decay_periods),
        "leakage_free": bool(step.leakage_free),
        "query": step.query,
        "relevant_experience_ids": list(step.relevant_experience_ids),
        "relevant_source_ids": list(step.relevant_source_ids),
        "required_after_compaction_ids": list(step.required_after_compaction_ids),
        "retained_after_compaction_ids": list(step.retained_after_compaction_ids),
        "reused_experience_ids": list(step.reused_experience_ids),
        "selected_source_ids": list(step.selected_source_ids),
        "session_id": case.session_id,
        "temporal_order_correct": bool(step.temporal_order_correct),
        "used_tokens": int(step.used_tokens),
    }


def verify_case_provenance_v3(case: AdversarialCorpusCaseV3) -> bool:
    """True when the generated digest matches inputs rebuilt from evaluator fields."""
    digest = case.provenance_digest()
    if not digest.startswith("sha256:") or len(digest) != 71:
        return False
    rebuilt = _roundtrip_evaluator_payload_v3(case)
    rebuilt_digest = "sha256:" + hashlib.sha256(_canonical_json(rebuilt).encode("utf-8")).hexdigest()
    return digest == rebuilt_digest


def _check_decay_boundary_v3(case: AdversarialCorpusCaseV3) -> bool:
    """At-floor record survives exactly on the floor; sub-floor raw decay is evicted."""
    if len(case.decay_base_strengths) != 2 or len(case.required_after_compaction_ids) != 2:
        raise MemoryQualityCorpusError("decay_fixture_invalid")
    projected = project_decay_strengths_v3(case.decay_base_strengths, case.decay_periods)
    factor = 0.5 ** int(case.decay_periods)
    floor = float(Memory.DECAY_FLOOR)
    raw_at_floor = float(case.decay_base_strengths[0]) * factor
    raw_subfloor = float(case.decay_base_strengths[1]) * factor
    floor_id = case.required_after_compaction_ids[0]
    subfloor_id = case.required_after_compaction_ids[1]
    retained = set(case.retained_after_compaction_ids)
    required = set(case.required_after_compaction_ids)
    return (
        raw_at_floor == floor
        and projected[0] == floor
        and raw_subfloor < floor
        and projected[1] == floor
        and floor_id in required
        and floor_id in retained
        and subfloor_id in required
        and subfloor_id not in retained
    )


def _metrics_dict(metrics: Any) -> Dict[str, Any]:
    return {
        "recall_mean": metrics.recall_mean,
        "attribution_precision_mean": metrics.attribution_precision_mean,
        "conflict_resolution_rate": metrics.conflict_resolution_rate,
        "temporal_order_rate": metrics.temporal_order_rate,
        "compaction_retention_mean": metrics.compaction_retention_mean,
        "budget_compliance_rate": metrics.budget_compliance_rate,
        "leakage_free_rate": metrics.leakage_free_rate,
        "experience_reuse_recall_mean": metrics.experience_reuse_recall_mean,
        "quality_score": metrics.quality_score,
        "cases": metrics.cases,
    }


def _validate_adapter(adapter: Any) -> None:
    record_trajectory = getattr(adapter, "record_trajectory", None)
    evaluate_sessions = getattr(adapter, "evaluate_sessions", None)
    if not callable(record_trajectory) or not callable(evaluate_sessions):
        raise MemoryQualityCorpusError("adapter_contract_invalid")


def evaluate_corpus_v3(
    adapter_factory: Callable[[], Any],
    seed: int = DEFAULT_SEED_V3,
    cases_per_category: int = DEFAULT_CASES_PER_CATEGORY_V3,
) -> Dict[str, Any]:
    """Record every generated case through the adapter and score it with the core evaluator.

    The expectation table is rebuilt from generator metadata on every call, so
    generator and evaluator must agree independently; disagreement lands in
    ``expectation_violations`` while contract breaches (bad adapter, unknown
    expectation key, missing entry) raise. No wall clock enters the report.
    """
    if not callable(adapter_factory):
        raise MemoryQualityCorpusError("adapter_factory_invalid")
    corpus = generate_corpus_v3(seed=seed, cases_per_category=cases_per_category)
    adapter = adapter_factory()
    _validate_adapter(adapter)

    expectations: Dict[str, Mapping[str, Any]] = {}
    for case in corpus:
        entry = expected_metrics_v3(case)
        if not entry:
            raise MemoryQualityCorpusError("expectation_entry_missing")
        expectations[case.case_id] = entry

    sessions: List[str] = []
    for case in corpus:
        if case.session_id not in sessions:
            sessions.append(case.session_id)
    for session_id in sessions:
        steps = tuple(step.to_trajectory_step() for step in corpus if step.session_id == session_id)
        adapter.record_trajectory(session_id, steps)
    multi_report = adapter.evaluate_sessions(tuple(sessions))

    evaluator = MemoryQualityEvaluator()
    per_case: Dict[str, Any] = {}
    inflation_detected = False
    for case in corpus:
        outcome = evaluator.evaluate_case(case.to_memory_quality_case())
        raw_attributed = case.attributed_source_ids
        if len(raw_attributed) != len(set(raw_attributed)) and outcome.attribution_precision == 1.0:
            inflation_detected = True
        provenance_verified = verify_case_provenance_v3(case)
        decay_ok = _check_decay_boundary_v3(case) if case.category == "decay_floor_boundary" else True
        actual = {
            "recall": outcome.recall,
            "attribution_precision": outcome.attribution_precision,
            "conflict_resolution": outcome.conflict_resolution,
            "temporal_order": outcome.temporal_order,
            "compaction_retention": outcome.compaction_retention,
            "budget_respected": outcome.budget_respected,
            "leakage_free": outcome.leakage_free,
            "experience_reuse_recall": outcome.experience_reuse_recall,
            "provenance_verified": provenance_verified,
            "decay_floor_boundary_respected": decay_ok,
        }
        violations = []
        for key, expected_value in expectations[case.case_id].items():
            if key not in actual:
                raise MemoryQualityCorpusError("expectation_key_unknown")
            if actual[key] != expected_value:
                violations.append("%s!=%r" % (key, expected_value))
        per_case[case.case_id] = {
            "category": case.category,
            "session_id": case.session_id,
            "recall": outcome.recall,
            "attribution_precision": outcome.attribution_precision,
            "conflict_resolution": outcome.conflict_resolution,
            "temporal_order": outcome.temporal_order,
            "compaction_retention": outcome.compaction_retention,
            "budget_respected": outcome.budget_respected,
            "leakage_free": outcome.leakage_free,
            "experience_reuse_recall": outcome.experience_reuse_recall,
            "provenance_verified": provenance_verified,
            "decay_floor_boundary_respected": decay_ok,
            "expectation_violations": violations,
        }

    quality_cases = tuple(case.to_memory_quality_case() for case in corpus)
    aggregate = _metrics_dict(evaluator.metrics(quality_cases))
    digest_payload = {
        "aggregate": aggregate,
        "case_ids": [case.case_id for case in corpus],
        "cases_per_category": cases_per_category,
        "corpus_digest": corpus_digest_v3(corpus),
        "corpus_size": len(corpus),
        "duplicate_attribution_inflation_detected": inflation_detected,
        "multi_session_total_cases": multi_report.total_cases,
        "per_case": per_case,
        "seed": seed,
        "session_ids": sessions,
    }
    report = dict(digest_payload)
    report["schema_version"] = CORPUS_SCHEMA_VERSION_V3
    report["claim_boundary"] = "deterministic_generated_adversarial_fixture_corpus_local_evaluator_only_not_external_model_benchmark"
    report["categories"] = {category: sum(1 for case in corpus if case.category == category) for category in sorted({case.category for case in corpus})}
    report["report_digest"] = "sha256:" + hashlib.sha256(_canonical_json(digest_payload).encode("utf-8")).hexdigest()
    return report


__all__ = [
    "AdversarialCorpusCaseV3",
    "CATEGORIES_V3",
    "CORPUS_SCHEMA_VERSION_V3",
    "DEFAULT_CASES_PER_CATEGORY_V3",
    "DEFAULT_SEED_V3",
    "MemoryQualityCorpusError",
    "corpus_digest_v3",
    "evaluate_corpus_v3",
    "expected_metrics_v3",
    "generate_corpus_v3",
    "project_decay_strengths_v3",
    "verify_case_provenance_v3",
]
