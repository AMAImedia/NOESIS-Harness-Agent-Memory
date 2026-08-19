# Gate 3 — Execution Assurance and Replay Boundary

**Status:** Local Python 3.14 evidence passed; native Windows/macOS and external lanes remain `not_run`.

## Contract

A governed child execution run has one immutable `request_id` and one canonical request fingerprint. The fingerprint covers the command arguments, resolved workspace, executable allowlist, environment, timeout and output budgets, network flag, skill manifest, skill identity and granted capabilities. The recovery ledger persists this fingerprint before execution.

A second invocation with the same `request_id` is not allowed to execute again after the run reaches a terminal state. It returns `execution_replay_denied`. A second invocation that reuses the `request_id` with a different request fingerprint returns `execution_request_identity_conflict`. An interrupted `running` record remains visible to recovery and must not be silently treated as a fresh run. It can transition to `recovered` only through an authenticated, scoped `recover` action with an injected handler that confirms the recovery transition. The action is explicit and idempotent; it does not claim rollback and it does not execute the child again.

The execution receipt is signed and persisted before the recovery record is marked terminal. A successful child run maps to recovery status `completed`; timeout, denial and failure map to their corresponding bounded terminal states. The recovery ledger never claims rollback unless an explicit recovery executor performs and confirms that mutation.

## Security invariants

| Invariant | Required result |
|---|---|
| Same request replay | Denied with `execution_replay_denied` |
| Same ID with changed command or policy inputs | Denied with `execution_request_identity_conflict` |
| Missing hardened backend for manifest-bound execution | Denied; no direct fallback |
| Network request without verified isolation | Denied fail-closed |
| Credential-like child output | Redacted and blocked |
| Receipt tampering or conflict | Rejected |
| Interrupted run | Explicit recovery-required state; only authenticated `recover` action may mark it recovered |
| Recovery without explicit action | Remains `running`/recovery-required; no automatic rollback or rerun |
| Automatic skill activation | Disabled; outside this runtime contract |

## Evidence boundary

The machine-readable artifact is [`GATE3_EXECUTION_ASSURANCE_EVIDENCE.json`](GATE3_EXECUTION_ASSURANCE_EVIDENCE.json). It records local deterministic evidence only. Linux/Bubblewrap availability does not imply Windows or macOS parity, and simulated or prepared Hermes/OpenCode/DeepSeek lanes do not count as external execution evidence.

The implementation remains separate from the memory and control plane. The parent process does not import or execute model-generated skill code, and executable skill activation requires a separate reviewed runtime contract.

## References

[1]: https://github.com/cloudflare/cloudflare-os "Cloudflare OS"
[2]: https://github.com/NousResearch/hermes-agent "Hermes Agent"
[3]: https://github.com/opencode-ai/opencode "OpenCode"

The referenced projects are design references and benchmark targets, not evidence that NOESIS has executed or surpassed them.
