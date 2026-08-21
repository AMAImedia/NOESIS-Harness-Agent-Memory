# Administrative Session and Coordinated Mutation Contract

This contract defines the bounded-local control-plane guarantees for operator sessions and reviewed administrative mutations. It does not claim external identity-provider integration, cross-file atomicity, native host parity, or external provider execution.

## Operator sessions

`OperatorSessionRegistry.open()` is idempotent only for the same active session identity and normalized scopes. A replay returns the existing record and never extends its original TTL. Reusing a session identifier with a different operator or different scopes fails closed with `operator_session_conflict`. Session creation uses a stable event identity rather than an event-count suffix.

Closed, expired, missing, or scope-mismatched sessions remain unauthenticated. Session lifecycle controls authorization only; it never performs promotion or activation.

## Coordinated mutation journal

`CoordinatedMutationJournal` records explicit `prepared`, `committed`, and `aborted` states. An identical prepare replay is a no-op. A changed operation, target, or receipt for an existing action identifier fails with `mutation_prepare_conflict`. Duplicate terminal events are idempotent. Commit-after-abort and abort-after-commit fail closed.

> The journal coordinates and exposes incomplete state; it does not claim atomicity across independent files or stores.

An incomplete prepared mutation is recoverable evidence requiring an explicit operator decision. The control plane never silently promotes an incomplete mutation or infers that a cross-store side effect completed.

## Evidence and boundaries

Machine-readable evidence is recorded in `docs/ADMIN_SESSION_IDEMPOTENCY_EVIDENCE.json` and `docs/COORDINATED_MUTATION_JOURNAL_EVIDENCE.json`. The focused contracts are tested under Python 3.14 with `ResourceWarning` treated as an error. Native Windows/macOS execution, external identity providers, and external A/B lanes remain `not_run` until matching pinned environments and operator-approved evidence exist.

## Runtime-owned learning policy

Portable deployment derives promotion capture policy from authoritative `TaskSessionStore` task ownership and session identity metadata. A task-event/session mismatch, missing owner, or disallowed derived scope returns a denied policy simulation. The portable path does not use a static fixture policy and still keeps evaluation, approval, promotion, and activation separately gated.
