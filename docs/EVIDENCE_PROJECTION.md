# Evidence Projection

Normative contract for the fail-closed evidence projection in [`noesis_harness/evidence_projection.py`](../noesis_harness/evidence_projection.py): a deterministic, read-only digest surface over locally committed evidence artifacts, built for the operator plane ([`noesis_harness/health_server.py`](../noesis_harness/health_server.py)).

## Purpose

The operator plane needs to see whether committed local evidence artifacts exist and still verify, without executing anything, mutating anything, or trusting an unverified document. `project_evidence()` answers exactly that: it reads [`docs/MULTI_AGENT_WORKLOAD_EVIDENCE.json`](MULTI_AGENT_WORKLOAD_EVIDENCE.json) and [`docs/MEMORY_QUALITY_EVIDENCE.json`](MEMORY_QUALITY_EVIDENCE.json), verifies the workload document's integrity digest, surfaces memory-quality corpus report digests as present-or-absent, and fails closed — a missing or corrupt file degrades to an unavailable status instead of raising. Deterministic core rule holds: no LLM, no network, no wall clock; the projection depends only on file contents and contains no timestamps.

## Projection schema (`noesis.evidence-projection.v1`)

`project_evidence(workload_path=None, memory_quality_path=None)` returns:

| Key | Content | Notes |
|---|---|---|
| `schema_version` | Always `noesis.evidence-projection.v1`. | Module constant `EVIDENCE_PROJECTION_SCHEMA`. |
| `claim_boundary` | Always `committed_local_evidence_read_only_fail_closed`. | Closed vocabulary, embedded in every projection. |
| `workload_evidence` | Status object for the workload evidence document. | See below. |
| `memory_quality_digests` | List of digest-presence entries from the memory-quality evidence document. | One entry per `adversarial_corpus_*` sub-report (sorted by key) plus one top-level entry. |

### `workload_evidence`

| Field | Available | Unavailable |
|---|---|---|
| `schema_version` | Document's own `schema_version` (e.g. `noesis.workload-evidence.v1`). | `""`, or the document value when it is a string even on failure. |
| `available` | `True` — file parsed, is a JSON object, has required fields. | `False` — always. |
| `digest_verified` | `True` only if the stored `output_digest` matches the recomputed canonical digest. | `False` — always. |
| `output_digest` | The stored `output_digest` (`sha256:` + 64 hex chars). | `""`, or the stored value when it is a non-empty string even on failure. |
| `reason` | `""` when verified; `output_digest_mismatch` otherwise. | Typed failure code; never empty. |

An available-but-unverified document (`reason = "output_digest_mismatch"`) is reported, not hidden: the operator sees the tamper signal without any claim being made on its behalf.

### `memory_quality_digests` entries

Each entry is `{corpus_schema_version, report_digest, digest_present}`:

- Per sub-report (`adversarial_corpus_*`, sorted by key): `corpus_schema_version` is that sub-report's `schema_version`; `report_digest` carries its `report_digest` when it is a non-empty string; `digest_present` is true only then.
- Final entry: the document's top-level `schema_version` with `report_digest = ""` and `digest_present = false`.

## Canonical-digest recomputation rule

`digest_verified` recomputes sha256 over the canonical JSON of the payload minus the `output_digest` key and compares to the stored value with `hmac.compare_digest` (constant-time):

```python
unsigned = {key: value for key, value in payload.items() if key != "output_digest"}
recomputed = "sha256:" + hashlib.sha256(
    json.dumps(unsigned, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
).hexdigest()
verified = hmac.compare_digest(recomputed, stored)
```

This matches the byte-stable digest emitted by the evidence generators, so a regenerated artifact verifies unchanged while any single-byte edit anywhere in the document breaks verification.

## Typed reasons vocabulary

`load_workload_evidence` never raises; failures map to a closed set of reason codes: `path_not_provided`, `file_missing`, `path_invalid`, `path_is_directory`, `file_unreadable`, `json_invalid` (decode or JSON parse error), `payload_not_object` (valid JSON that is not an object), `required_field_missing` (missing/empty `schema_version` or `output_digest`), and `output_digest_mismatch` after verification fails. Every unavailable result carries `available = false`, `digest_verified = false`, and a non-empty typed reason.

`load_memory_quality_digests` never raises either: missing, unreadable, invalid, or non-object documents yield an empty list, and a missing or empty sub-report digest is surfaced honestly as `digest_present = false` rather than dropped or fabricated. Digest presence is attested only; corpus digest verification needs the corpus fixtures and is out of scope here.

## Integration

[`HealthServer.operator_snapshot`](../noesis_harness/health_server.py) accepts an optional keyword-only `evidence_projection` parameter: `None` (default) leaves the snapshot unchanged — the key is absent, so existing consumers see identical bytes; a supplied projection is attached verbatim under `evidence_projection`. The projection is built by the caller; the server never reads evidence files itself.

## Related tests

- [`tests/test_evidence_projection.py`](../tests/test_evidence_projection.py) — real committed workload evidence verifies against its stored digest; a single-byte tampered copy reports `output_digest_mismatch`; missing and corrupt files fail closed with typed reasons; memory-quality digest entries (two corpus sub-reports plus the top-level entry) match the pinned evidence document; repeated projections are byte-equal; defaults are safe when paths are absent; `operator_snapshot` excludes the key by default and embeds a supplied projection verbatim.

## Provenance

Patterns borrowed per repo discipline: deepseek-harness fail-closed verification discipline (missing/corrupt input degrades to a typed unavailable status instead of raising, `hmac.compare_digest` over canonical JSON); LoopX read-only projections (a deterministic replay-style view over committed state, never mutating it). Canonical-JSON digest verification follows the signed report bundle / lifecycle audit ingestion lineage already ported in this repo; the bounded-snapshot convention follows the HealthServer `evidence_aggregate` pattern.

## Claim boundary

The projection is a read-only attestation of LOCAL committed files at read time: it states that named documents exist, parse, and whose integrity digests verify against their contents on this machine. It does not re-run the workloads, does not validate what the documents claim about executions, does not verify corpus digests, and is not external or comparative evidence of any kind.
