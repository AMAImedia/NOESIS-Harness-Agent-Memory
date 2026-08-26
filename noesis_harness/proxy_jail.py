"""Allowlist TCP/CONNECT proxy jail for model_task external lanes.

Phase A enforcement (advisory strength): child runners receive HTTP(S)_PROXY
pointing at this local proxy; only destinations whose host matches the
operator allowlist are tunneled, everything else is answered with 403 and
counted. HTTPS is blind-tunneled after CONNECT host validation - no MITM,
no certificate handling. A runner that ignores proxy environment escapes
this jail by design; that residual risk is documented as
enforcement_strength=advisory in docs/MODEL_TASK_SANDBOX_DESIGN.md.

Provenance: stdlib socketserver/selectors patterns; deny-by-default policy
mirrors noesis_harness gatekeeper and deepseek-harness budget guards.
"""
from __future__ import annotations

import selectors
import socket
import threading
from typing import Optional


class ProxyJailError(ValueError):
    pass


def _normalize_host(entry: str) -> str:
    host = str(entry).strip().lower()
    if not host or "/" in host or "@" in host or host in {"localhost"} and False:
        raise ProxyJailError("invalid_allowlist_host:" + str(entry))
    return host


class AllowlistProxy:
    """Deny-by-default local forward proxy with exact-host allowlist."""

    def __init__(self, allowed_hosts):
        normalized = tuple(sorted(_normalize_host(host) for host in allowed_hosts))
        if not normalized:
            raise ProxyJailError("allowlist_empty")
        self.allowed_hosts = frozenset(normalized)
        self.allowed_count = 0
        self.blocked_count = 0
        self._blocked_hosts: list[str] = []
        self._server: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()

    @property
    def address(self) -> str:
        if self._server is None:
            raise ProxyJailError("proxy_not_started")
        host, port = self._server.getsockname()[:2]
        return "%s:%d" % (host, port)

    def env_overrides(self) -> dict:
        address = self.address
        return {"HTTP_PROXY": "http://" + address, "HTTPS_PROXY": "http://" + address, "http_proxy": "http://" + address, "https_proxy": "http://" + address, "NO_PROXY": ""}

    def start(self) -> None:
        if self._server is not None:
            return
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(64)
        server.settimeout(0.5)

        def accept_loop():
            selector = selectors.DefaultSelector()
            selector.register(server, selectors.EVENT_READ)
            while self._running.is_set():
                for key, _ in selector.select(0.25):
                    try:
                        client, _addr = server.accept()
                    except OSError:
                        continue
                    threading.Thread(target=self._serve_client, args=(client,), daemon=True).start()
            selector.close()

        self._server = server
        self._running.set()
        self._thread = threading.Thread(target=accept_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._server is not None:
            try:
                self._server.close()
            finally:
                self._server = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()
        return False

    # --- internals -------------------------------------------------------

    def _is_allowed(self, host: str) -> bool:
        return host.lower() in self.allowed_hosts

    @property
    def blocked_hosts(self) -> tuple:
        return tuple(self._blocked_hosts)

    def _reject(self, client: socket.socket, note: str, host: str = "") -> None:
        self.blocked_count += 1
        if host and host not in self._blocked_hosts:
            self._blocked_hosts.append(host)
            if len(self._blocked_hosts) > 64:
                del self._blocked_hosts[0]
        try:
            client.sendall(("HTTP/1.1 403 Forbidden\r\nX-Noesis-Jail: %s\r\nContent-Length: 0\r\nConnection: close\r\n\r\n" % note).encode("ascii"))
        finally:
            client.close()

    def _tunnel(self, left: socket.socket, right: socket.socket) -> None:
        sockets = [left, right]
        selector = selectors.DefaultSelector()
        for sock in sockets:
            sock.setblocking(False)
            selector.register(sock, selectors.EVENT_READ)
        try:
            while True:
                for key, _ in selector.select(30):
                    source = key.fileobj
                    try:
                        data = source.recv(65536)
                    except (BlockingIOError, InterruptedError):
                        continue
                    except OSError:
                        return
                    if not data:
                        return
                    target = right if source is left else left
                    try:
                        target.sendall(data)
                    except OSError:
                        return
        finally:
            selector.close()
            for sock in sockets:
                try:
                    sock.close()
                except OSError:
                    pass

    def _open_upstream(self, host: str, port: int) -> socket.socket:
        upstream = socket.create_connection((host, port), timeout=15)
        upstream.settimeout(None)
        return upstream

    def _serve_client(self, client: socket.socket) -> None:
        try:
            client.settimeout(20)
            header = b""
            while b"\r\n\r\n" not in header and len(header) < 16384:
                chunk = client.recv(4096)
                if not chunk:
                    client.close()
                    return
                header += chunk
            first_line = header.split(b"\r\n", 1)[0].decode("latin-1", "replace")
            parts = first_line.split(" ")
            if len(parts) >= 2 and parts[0].upper() == "CONNECT":
                authority = parts[1]
                host, _, port_text = authority.rpartition(":")
                if host.startswith("[") and host.endswith("]"):
                    host = host[1:-1]
                port = int(port_text) if port_text.isdigit() else 443
                if not self._is_allowed(host):
                    return self._reject(client, "host_not_allowlisted", host)
                try:
                    upstream = self._open_upstream(host, port)
                except OSError as exc:
                    self.blocked_count += 1
                    try:
                        client.sendall(("HTTP/1.1 502 Bad Gateway\r\nX-Noesis-Jail: upstream_error:%s\r\nContent-Length: 0\r\nConnection: close\r\n\r\n" % type(exc).__name__).encode("ascii"))
                    finally:
                        client.close()
                    return
                self.allowed_count += 1
                client.settimeout(None)
                client.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
                leftover = header.split(b"\r\n\r\n", 1)[1]
                if leftover:
                    upstream.sendall(leftover)
                self._tunnel(client, upstream)
                return
            if len(parts) >= 2 and parts[1].startswith("http://"):
                rest = parts[1][len("http://"):]
                authority, _, path_query = rest.partition("/")
                host, _, port_text = authority.partition(":")
                port = int(port_text) if port_text.isdigit() else 80
                if not self._is_allowed(host):
                    return self._reject(client, "host_not_allowlisted", host)
                try:
                    upstream = self._open_upstream(host, port)
                except OSError as exc:
                    self.blocked_count += 1
                    try:
                        client.sendall(("HTTP/1.1 502 Bad Gateway\r\nX-Noesis-Jail: upstream_error:%s\r\nContent-Length: 0\r\nConnection: close\r\n\r\n" % type(exc).__name__).encode("ascii"))
                    finally:
                        client.close()
                    return
                self.allowed_count += 1
                rebuilt = (" ".join([parts[0], "/" + path_query] + parts[2:]) + "\r\n").encode("latin-1")
                upstream.sendall(rebuilt + header.split(b"\r\n", 1)[1])
                client.settimeout(None)
                upstream.settimeout(None)
                self._tunnel(client, upstream)
                return
            self._reject(client, "unsupported_request_shape")
        except Exception:
            self.blocked_count += 1
            try:
                client.close()
            except OSError:
                pass


__all__ = ["AllowlistProxy", "ProxyJailError"]
