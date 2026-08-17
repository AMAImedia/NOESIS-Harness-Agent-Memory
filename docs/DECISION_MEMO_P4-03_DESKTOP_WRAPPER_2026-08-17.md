# NOESIS P4-03 — Desktop wrapper decision memo

**Дата:** 2026-08-17  
**Репозиторий:** `AMAImedia/NOESIS-Harness-Agent-Memory`  
**Статус:** Decision memo; никаких GitHub settings или visibility changes не выполняется

## Executive decision

Рекомендуется **не добавлять Electron или Tauri в core сейчас**. Текущий stdlib-first control plane должен оставаться источником истины и самостоятельным portable baseline. Native wrapper следует рассматривать как отдельный optional packaging layer после появления реальных Windows и macOS CI runners.

Для будущего desktop shell предпочтителен **Tauri**, но только как отдельный проектный слой с Rust/IPC review, capability allowlist, native signing/packaging и platform smoke tests. Electron не следует выбирать как default: его security surface включает Chromium, Node.js, Electron, npm dependencies и application code; официальные рекомендации требуют context isolation, process sandboxing, restrictive CSP, IPC sender validation и запрета Node integration для remote content [1].

## Comparison

| Критерий | Stdlib-first control plane | Tauri | Electron |
|---|---|---|---|
| Current dependency policy | Полностью соответствует local-first stdlib-only core | Потребуется Rust toolchain и отдельный native build layer | Потребуются Node/npm ecosystem и bundled runtime |
| Audit surface | Минимальный: Python package, loopback HTTP, explicit supervisor | Rust core, WebView, IPC, capabilities, scopes и plugins | Chromium, Node.js, Electron, IPC, npm dependencies и application code |
| Runtime footprint | Минимальный; системный Python уже требуется | Обычно меньше, поскольку использует OS WebView и не ships bundled runtime [2] | Обычно существенно больше из-за bundled Chromium/Node runtime |
| Security boundary | Explicit Python API, loopback default, token auth for non-loopback | WebView ↔ Rust IPC; capabilities/scopes должны быть tightly allowlisted [3] | Renderer ↔ main/Node boundary; misconfiguration can elevate web content |
| Portability status in NOESIS | Windows portable boundary verified; macOS branch simulated | Native CI and signing still required | Native CI and packaging still required |
| Strategic fit | **Best current baseline** | **Best future optional shell** | Not recommended as default |

## Security reasoning

Electron’s own security documentation emphasizes that displaying arbitrary untrusted content is a severe risk and that remote content must not receive Node integration. It also recommends process sandboxing, restrictive CSP, limited navigation and validated IPC senders [1]. These requirements would duplicate boundaries already implemented in NOESIS while adding a substantially larger dependency/runtime surface.

Tauri has a more suitable shape for a future shell because the WebView is separated from a Rust core through IPC, with capabilities and scopes controlling exposed commands [3]. Tauri also relies on the operating-system WebView rather than bundling one, which reduces binary size but creates a host-WebView update and compatibility responsibility [2] [3]. Tauri is **not** an OS-level sandbox: Tauri’s documentation notes that core/plugin code has access to available system resources [3]. Therefore, a Tauri wrapper would not replace NOESIS’s deny-by-default supervisor, skill import gates or agent isolation corpus.

The current Python control plane should remain loopback-only by default. Python’s `http.server` documentation explicitly warns that it is not recommended for production and implements only basic security checks [4]. NOESIS’s current design correctly treats it as a local control plane, not an internet-facing server.

## Recommended implementation sequence

First, keep the existing stdlib UI/API and child-runtime supervisor as the canonical contract. Second, add native CI jobs for Windows and macOS arm64 that verify startup, random loopback ports, data-root preservation, clean shutdown, auth and artifact checksums. Third, if a native shell is still needed, create an isolated `desktop/tauri/` layer that communicates only with the existing loopback contract and never receives provider credentials. Fourth, apply a separate threat model to IPC commands, update/signing, WebView navigation, deep links, file access and crash recovery. Electron should be reconsidered only if a concrete requirement cannot be satisfied by the browser UI or Tauri.

## Owner decisions required

| Decision | Recommendation | Current status |
|---|---|---|
| Keep repository private | Yes until explicit release approval | Waiting for owner |
| Enable branch protection | Yes after selecting required checks | Waiting for owner |
| Choose wrapper | Defer; prefer optional Tauri later | Waiting for owner |
| Native macOS arm64 runner | Required before native artifact claim | Not available in current environment |
| Windows `.exe` claim | Do not claim without Windows packaging runner | Not available in current environment |
| Public release | No automatic visibility change | Waiting for owner |

## References

[1]: https://electronjs.org/docs/latest/tutorial/security "Electron Security"

[2]: https://v2.tauri.app/concept/architecture/ "Tauri Architecture"

[3]: https://v2.tauri.app/security/ "Tauri Security"

[4]: https://docs.python.org/3/library/http.server.html "Python http.server documentation"
