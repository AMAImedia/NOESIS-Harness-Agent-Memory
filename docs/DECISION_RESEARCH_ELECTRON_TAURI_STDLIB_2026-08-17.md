# External research notes — Electron/Tauri/stdlib

## Sources

1. Electron Security: https://electronjs.org/docs/latest/tutorial/security
   Electron states that its security depends on Chromium, Node.js, Electron, npm dependencies and application code. The official checklist recommends current Electron versions, context isolation, process sandboxing, restrictive CSP, limited navigation/window creation, sender validation for IPC and avoiding exposing Electron APIs to untrusted content. Electron also warns not to load and execute remote code with Node.js integration enabled.

2. Tauri Architecture: https://v2.tauri.app/concept/architecture/
   Tauri combines Rust application code with an operating-system WebView. It uses message passing between WebView and Rust APIs, compiles the application into a final binary, and does not ship a bundled runtime in the same way as Electron. Its ecosystem includes Rust crates, a bundler and cross-platform tooling for macOS, Windows and Linux.

3. Tauri Security: https://v2.tauri.app/security/
   Tauri describes a trust boundary between frontend WebView code and Rust core code. IPC, capabilities and scopes are used to control exposed system resources. Tauri notes that core/plugin code has access to available system resources, while WebView access is limited to exposed commands. Tauri relies on the operating-system WebView rather than bundling one, which is a security/update trade-off. Tauri also states that application security depends on Tauri, Rust/npm dependencies, application code and the host device.

4. Python http.server: https://docs.python.org/3/library/http.server.html
   Python documents http.server as a basic HTTP server implementation and explicitly warns that it is not recommended for production because it implements only basic security checks. This supports keeping the NOESIS stdlib control plane local-first, loopback-only by default and not presenting it as an internet-facing production server.

## Decision implications for NOESIS

Electron would add a large Chromium/Node/runtime and dependency security surface; it should not be introduced merely to wrap the existing read-only UI. Tauri is a more suitable future optional shell when native desktop packaging is required, but its Rust core/IPC/capability boundary would need a separate security review and native macOS/Windows CI. The current stdlib-first control plane remains the smallest auditable baseline and should remain the source of truth behind any future shell.
