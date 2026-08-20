# Durable Turn Checkpoints

This is the normative contract for crash-safe per-turn persistence in the local-first NOESIS loop. Checkpointing is **sequential, atomic, checksum-verified, recoverable, and non-executing**.

## Contract

Each run is initialized by a `run_id`. A checkpoint may advance only from `turn = n` to `turn = n + 1`; skipped turns and replayed turn numbers are rejected. The persisted record contains the schema version, run and turn identifiers, status, JSON state, output digest, state digest, previous state digest, and creation time.

State is serialized canonically with sorted keys and compact separators. The record digest is SHA-256 over the canonical payload. SQLite uses WAL mode and a transaction that writes the checkpoint and updates the run projection together. The connection is closed on every path, including commit and exception paths.

| Status | Meaning | Recovery behavior |
|---|---|---|
| `running` | Run may accept the next sequential turn. | Resume from the latest verified checkpoint. |
| `checkpointed` | A turn was durably persisted and the run is continuing. | Resume at `turn + 1`. |
| `completed` | The latest turn marked the run complete. | Preserve the final state; a caller may explicitly reopen it. |
| `interrupted` | The loop stopped between turns or during operator cancellation. | Recover the last verified state without inventing a turn. |
| `corrupted` | A checksum, schema, state digest, or chain check failed. | Fail closed and quarantine outside the verified path. |

## Recovery and adversarial requirements

Recovery verifies the latest record and the complete previous-digest chain before changing a run back to `running`. A malformed payload, mismatched record digest, mismatched state digest, chain discontinuity, or unknown schema is rejected as `checkpoint_corrupt` or `checkpoint_chain_mismatch`. Interrupted writes must leave either the previous committed state or the complete next record; a half-record is never accepted.

The checkpoint store persists state and evidence only. It does not execute callbacks, import generated code, infer approvals, or activate skills. A higher-level loop may call a deterministic callback and then commit its result, but callback execution remains subject to the separate child-runtime and capability contracts.

## Implementation and evidence

The stdlib-only implementation is [`noesis_harness/turn_checkpoint.py`](../noesis_harness/turn_checkpoint.py). Focused tests are [`tests/test_turn_checkpoint.py`](../tests/test_turn_checkpoint.py), covering sequential rejection, restart recovery, interrupted-turn recovery, corruption rejection, chain verification, and connection hygiene. The current evidence is local Python 3.14 evidence only; native host and external harness claims remain `not_run` until matching environments are available.
