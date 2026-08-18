# Release Audit and External Readiness Boundary

The read-only release audit now consumes `docs/EXTERNAL_EVIDENCE_READINESS_MATRIX.json` as a claim guard. It validates the readiness schema, the four-status vocabulary, lane presence, and `native_or_external_execution_claim == false` before treating the repository audit as structurally valid.

The readiness artifact is allowed to be `not_run` during a local/private release candidate. This is expected when exact Hermes, OpenCode, and DeepSeek Harness revisions or matching hosts are unavailable. The release audit reports that state under `external_readiness`; it does not convert it into a comparative pass or failure score.

| Audit result | Interpretation |
|---|---|
| `external_readiness.errors=[]` and `overall_status=not_run` | The evidence guard is structurally valid; external execution has not been demonstrated. |
| `external_readiness.errors=[]` and `overall_status=blocked` | The matrix detected an integrity, identity, replay, duplicate, or protocol conflict. |
| `external_readiness.errors` non-empty | The readiness artifact is invalid and the release audit fails closed. |
| `native_or_external_execution_claim=true` | Invalid for this local release boundary; the release audit fails closed. |

This integration is a local evidence-plumbing gate. It does not create native Windows/macOS evidence, third-party execution evidence, or a superiority ranking.
