# Следующий high-leverage gate: Cross-Platform Task Execution Parity

## Цель

Связать уже реализованные durable memory, task/session API, skill governance, multi-agent coordination и sandbox backends в один проверяемый execution path, который одинаково ограничивает side effects на Linux, macOS и Windows. Этот gate должен производить сопоставимое evidence, а не только новые интерфейсы.

## Почему это следующий gate

Локально уже доказаны provenance-aware memory reuse, scoped skill discovery, cooperative cancellation, explicit merge authorization, Linux/Bubblewrap conformance и process-tree termination. Оставшийся разрыв с ведущими агентами — не ещё один isolated feature, а отсутствие одинакового end-to-end proof на target OS и внешних pinned systems.

## Четыре lane

| Lane | Acceptance criteria | Current state |
|---|---|---|
| A. Native sandbox parity | Same filesystem, network, shell, output, timeout, credential and descendant tests; backend identity and host facts recorded | Linux passed; macOS/Windows `not_run` until matching hosts |
| B. Task/session parity | `session.create → task.create → request_execution → approval → child run → SSE → recovery` with bounded events and audit receipt | Local API/bridge implemented; end-to-end native UI smoke remains next |
| C. Memory/skill governance | Reuse requires provenance/scope/sensitivity; discovery is read-only; execution requires manifest + Gatekeeper + child backend | Local verified |
| D. External benchmark readiness | Exact revisions, pinned environment digest, identical task suite, signed evidence, no ranking when a lane is missing | Contract and fail-closed runner implemented; Hermes/OpenCode/DeepSeek execution `not_run` |

## Stop conditions

The gate must stop and report `not_run` when the host OS, Python 3.14 runtime, backend binary, exact upstream revision, operator approval or signing key is missing. A fixture may validate plumbing but cannot become an external score. Any credential-like output, cross-agent leakage, stale lease, unauthorized capability or backend mismatch fails the lane.

## Execution order

1. Run Linux full conformance and task/session smoke locally.
2. Run identical operator bundle on matching macOS and Windows Python 3.14 hosts.
3. Pin Hermes, OpenCode and DeepSeek Harness revisions and capture environment digests.
4. Execute the same approved task suite through connector-neutral adapters.
5. Ingest only signed records whose execution/status/hash combinations pass strict validation.
6. Publish a comparison only if all systems and metrics are present; otherwise publish a coverage report with explicit `not_run` states.

## Success definition

Success is a reproducible, signed, cross-platform evidence package with zero unauthorized side effects and explainable recovery—not a predetermined claim that NOESIS is superior. Any “best in world” statement remains prohibited until comparable external A/B results support it.
