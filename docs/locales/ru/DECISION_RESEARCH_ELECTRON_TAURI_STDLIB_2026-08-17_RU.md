# Заметки внешнего исследования — Electron/Tauri/stdlib

## Источники

1. Electron Security: https://electronjs.org/docs/latest/tutorial/security
   Electron утверждает, что его безопасность зависит от Chromium, Node.js, Electron, npm-зависимостей и application code. Официальный checklist рекомендует актуальные версии Electron, context isolation, process sandboxing, restrictive CSP, ограниченные navigation/window creation, sender validation для IPC и не выставлять Electron APIs в untrusted content. Electron также предупреждает не загружать и исполнять remote code с включённой Node.js integration.

2. Tauri Architecture: https://v2.tauri.app/concept/architecture/
   Tauri сочетает Rust-код приложения с OS WebView. Используется message passing между WebView и Rust APIs, приложение компилируется в финальный binary и не поставляет bundled runtime так, как Electron. Экосистема включает Rust crates, bundler и кросс-платформенный tooling для macOS, Windows и Linux.

3. Tauri Security: https://v2.tauri.app/security/
   Tauri описывает trust boundary между frontend WebView-кодом и Rust core-кодом. IPC, capabilities и scopes управляют выставленными системными ресурсами. Tauri отмечает, что core/plugin-код имеет доступ к доступным системным ресурсам, тогда как доступ WebView ограничен выставленными командами. Tauri полагается на OS WebView вместо bundling, что является компромиссом по безопасности/обновлениям. Tauri также указывает, что безопасность приложения зависит от Tauri, Rust/npm-зависимостей, application code и хост-устройства.

4. Python http.server: https://docs.python.org/3/library/http.server.html
   Python документирует http.server как базовую реализацию HTTP-сервера и явно предупреждает, что он не рекомендован для production, поскольку реализует лишь базовые security checks. Это поддерживает требование держать stdlib control plane NOESIS local-first, loopback-only по умолчанию и не представлять его как production internet-facing сервер.

## Следствия для решений NOESIS

Electron добавит большой surface безопасности из Chromium/Node/runtime и зависимостей; его не следует вводить только ради обёртки существующего read-only UI. Tauri — более подходящий будущий optional shell, когда требуется native desktop packaging, но его Rust core/IPC/capability boundary потребует отдельного security review и native macOS/Windows CI. Текущий stdlib-first control plane остаётся наименьшим auditable baseline и должен оставаться source of truth за любым будущим shell.
