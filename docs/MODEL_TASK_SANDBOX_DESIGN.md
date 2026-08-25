# Model Task Network-Restricted Execution Backend Design

Status: design + scaffold (Gate 7 blocker work). No execution runtime is bound
in this change; every claim below is scoped accordingly. Schemas referenced:
`noesis.model-task-sandbox-inventory.v1`, `noesis.model-task-egress-policy.v1`.

## 1. Problem

`scripts/external_runner_contract.py` distinguishes two execution classes via
`task_execution_class`: `version_smoke` (no egress needed) and `model_task`
(pinned LLM-API calls required). Lane policy is deny-by-default
(`outside_access: "deny"`), and the operator preflight
(`docs/PINNED_LANE_OPERATOR_PREFLIGHT.md`) requires a deny-by-default network
posture as a readiness precondition.

Today the only containment applied to an external runner is adapter-side:
environment sanitization (credential stripping), disposable workspace, pinned
argv. That is process hygiene, NOT a network boundary. Nothing prevents a
model_task child from opening arbitrary sockets to any host. Conversely,
nothing lets us grant the one allowed egress (the model API) while keeping the
deny posture for everything else. Gate 7 therefore blocks: we cannot honestly
claim network containment for `model_task` lanes, so those lanes stay
`not_run` indefinitely.

Required capability: per-lane egress that is denied everywhere except an
explicitly allowlisted set of model-api hosts, with honest reporting of what
is and is not enforced.

## 2. Options analysis (Windows-first)

### 2.1 AppContainer / LPAC with internet capability

A real kernel-enforced boundary. The child runs inside an AppContainer (or
Less-Privileged AppContainer) whose token only permits `internetClient`
egress; filesystem writes outside granted paths are ACL-denied. This matches
the desired policy almost exactly.

Costs on this repo's terms:

- Requires creating an AppContainer profile and launching a signed or
  allowlisted executable (package identity, or explicit profile + ACE grants),
  plus token/runas plumbing.
- Native Win32 tooling sits outside the stdlib-only constraint
  (`AGENTS.md` rule 1); it must live behind a pluggable backend callback.
- Per-executable profile management and cleanup are operator burden.

Verdict: real boundary, correct long-term target. Deferred to Phase B.

### 2.2 Windows Filtering Platform (WFP) per-app filter

Kernel-layer per-application filtering is technically the strongest option,
but it requires an admin-elevated provider/sublayer installation and borders
on driver-signing territory. Not shippable inside a portable stdlib-only
harness, fragile across Windows editions, and far outside "no install
friction". Verdict: rejected for this repo (documented, not built).

### 2.3 Job Objects

Job Objects control CPU, memory, UI restrictions, and process-tree lifetime.
They have NO network control whatsoever. Honest rejection as a network
boundary; they remain useful elsewhere for tree cancellation
(`process_control`), which is out of scope here.

### 2.4 Proxy jail (chosen Phase A)

Force the lane's `HTTP_PROXY`/`HTTPS_PROXY` to a local loopback filtering
proxy (stdlib `http.server`-based) that permits CONNECT tunneling ONLY to
configured model-api hosts; every other CONNECT/host request is denied and
logged. Properties:

- Works without admin, without drivers, without MITM: the proxy tunnels
  (`CONNECT`), it does not decrypt, so no certificate machinery is needed —
  provided the runner honors proxy environment variables.
- Caveat (accepted, documented): enforcement is advisory. A child that ignores
  proxy env — raw sockets, its own resolver, non-HTTP protocols — escapes the
  jail. We label this `enforcement_strength: advisory` in the egress policy
  rather than hiding it.

Verdict: chosen interim Phase A because it unblocks model_task lanes with
zero privilege escalation while Phase B matures.

### 2.5 Linux reference: bubblewrap `--unshare-net`

`noesis_harness/sandbox_bwrap.py` already provides kernel-enforced network
isolation (`--unshare-all --unshare-net`). The reference pattern for
model_task egress there is: unshare net, then run egress through an explicit
helper. Our Phase A checks deliberately mirror the bwrap conformance checks
(`network_policy_declared`, fail-closed statuses) so the two backends report
comparable evidence.

## 3. Chosen phased plan

### Phase A — proxy-jail scaffold (this change)

Delivered now, in `noesis_harness/model_task_sandbox.py`:

- `ModelTaskSandboxBackend(backend_id="model-task-proxy", host_platform="any")`
  with `allowlisted_hosts` validated fail-closed at construction (empty or
  invalid host raises; schemes, ports, wildcards, paths rejected).
- `available=False` until an injected `verify_proxy_boundary()` callback
  returns True; verifier exceptions are failures, not passes.
- `run()` returns a blocked `SandboxResult` without spawning anything; even a
  verified boundary reports `model_task_execution_runtime_not_bound` until the
  runtime executor is wired by the operator.
- `proxy_env_for(allowlist)` builds the deterministic
  `HTTP(S)_PROXY`/`NO_PROXY` environment pointing at `127.0.0.1:<port>`;
  loopback targets are exempted from the jail, allowlisted hosts are not.
- Zero subprocess in the module, asserted by test (mirrors
  `test_sandbox_windows.py::test_module_never_imports_subprocess`).

Planned companion runtime (separate module, not in this change):
`scripts/model_task_proxy.py` — loopback-only listener, CONNECT allowlist,
deny log, health probe endpoint. The scaffold never starts it; operators do.

Verification probes (Phase A):

| Probe | Kind | Pass condition |
|---|---|---|
| A1 static | unit | module has no `subprocess`; default backend unavailable |
| A2 static | unit | `proxy_env_for` shape: upper+lower entries, NO_PROXY = loopback only, allowlisted host absent from NO_PROXY |
| A3 static | unit | allowlist validation fails closed on empty/invalid input |
| A4 runtime | integration, later | denied-host CONNECT through proxy returns denial + log entry |
| A5 runtime | integration, later | allowed-host CONNECT tunnels end-to-end |
| A6 honesty | integration, later | a child ignoring proxy env CAN reach the network directly; result recorded as known escape, not hidden |

Phase A failure modes:

| Mode | Effect | Disposition |
|---|---|---|
| Proxy not started | all jailed egress hits a dead loopback port → fails closed | safe by construction |
| Runner honors proxy but host not allowlisted | CONNECT denied + logged | intended deny |
| Runner ignores proxy env | escape; direct sockets work | accepted advisory gap, surfaced by A6 and claim boundary |
| Proxy crashes mid-run | egress breaks closed | safe direction; retry policy is operator-side |
| DNS divergence (proxy resolves names itself) | possible rebinding concerns | open item for runtime phase; document resolution pinning then |

### Phase B — AppContainer LPAC backend

Target state, same honesty contract:

- Checklist: signed/allowlisted executable or package identity; LPAC profile
  with `internetClient` capability only; FS write scope limited to disposable
  workspace via ACL deny; restricted-token fallback where LPAC is unavailable.
- Verification probes: B1 container token inspection of spawned child;
  B2 denied-FS write attempt fails; B3 non-allowlisted socket connect fails at
  the OS layer; B4 conformance via `sandbox_backend.run_conformance`.
- Failure modes: unsigned binary refused (fail closed); profile creation
  failure → unavailable, never silent fallback; capability over-grant → probe
  B3 fails → backend marked failed.

## 4. Claim boundary

Stated last, per house style (`docs/NATIVE_EVIDENCE_HONESTY_GATE.md`):

- Phase A is NOT an OS-level network boundary. It is environment-based,
  advisory containment. Children that ignore proxy variables are not
  contained; probe A6 exists to keep that fact measured, not forgotten.
- No MITM, no TLS interception, no content inspection is claimed or planned.
- No credential safety beyond existing env sanitization is claimed.
- Nothing ran. There is no receipt, score, or execution evidence in this
  change; `execution_claim` is `not_run` everywhere by construction.
- Current evidence is structural only: deterministic environment generation,
  fail-closed allowlist validation, zero-subprocess guarantee, blocked
  results on every path until a verified boundary AND a bound runtime exist.
- Runtime receipts require the Phase A proxy runtime, probes A4–A6 passing
  under operator approval, per `docs/PINNED_LANE_OPERATOR_PREFLIGHT.md`.
