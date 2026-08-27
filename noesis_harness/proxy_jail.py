"""Allowlist TCP/CONNECT proxy jail for model_task external lanes.

Phase A enforcement (advisory strength): child runners receive HTTP(S)_PROXY
pointing at this local proxy; only destinations whose host matches the
operator allowlist are tunneled, everything else is answered with 403 and
counted. HTTPS is blind-tunneled after CONNECT host validation - no MITM,
no certificate handling. A runner that ignores proxy environment escapes
this jail by design; that residual risk is documented as
enforcement_strength=advisory in docs/MODEL_TASK_SANDBOX_DESIGN.md.

Phase A hardening (evasion closed): hostnames are canonicalized on both the
allowlist and the request side (trailing dots stripped, lowercased, embedded
NUL/whitespace and '..' rejected); CONNECT authorities are parsed strictly
(required numeric 1..65535 port, bracketed IPv6, no ambiguous input) and any
malformed authority is answered 400 + counted without tunneling; plain HTTP
absolute-URI requests are rejected when the Host header disagrees with the
request target (split-brain, fail-closed); first-line and total-header caps
close with 431. Every reject path bumps blocked_count and records the host
(or '<malformed>').

Provenance: stdlib socketserver/selectors patterns; deny-by-default policy
mirrors noesis_harness gatekeeper and deepseek-harness budget guards.
"""
from __future__ import annotations

import selectors
import socket
import threading
from typing import Optional

MAX_FIRST_LINE = 16384
MAX_HEADER = 65536

_STATUS_PHRASES = {
    400: "Bad Request",
    403: "Forbidden",
    431: "Request Header Fields Too Large",
    502: "Bad Gateway",
}


class ProxyJailError(ValueError):
    pass


def _canonical_host(host: str) -> str:
    canonical = str(host).strip().lower().rstrip(".")
    if not canonical:
        raise ProxyJailError("invalid_host:" + str(host))
    if "/" in canonical or "@" in canonical or "\x00" in canonical or ".." in canonical:
        raise ProxyJailError("invalid_host:" + str(host))
    if any(ch.isspace() for ch in canonical):
        raise ProxyJailError("invalid_host:" + str(host))
    return canonical


def _normalize_host(entry: str) -> str:
    try:
        return _canonical_host(entry)
    except ProxyJailError:
        raise ProxyJailError("invalid_allowlist_host:" + str(entry))


def _split_authority(authority: str, default_port: Optional[int]) -> Optional[tuple]:
    """Parse an authority into (canonical_host, port) or None when malformed.

    IPv6 addresses must be bracket-wrapped. A port is required when
    default_port is None (CONNECT) and must be numeric in 1..65535. A colon
    with an empty port, an empty host, or any ambiguous shape yields None so
    the caller can fail closed without tunneling.
    """
    if not authority:
        return None
    had_colon = False
    if authority.startswith("["):
        close = authority.find("]")
        if close < 0:
            return None
        host = authority[1:close]
        tail = authority[close + 1:]
        if tail == "":
            port_text = ""
        elif tail.startswith(":"):
            had_colon = True
            port_text = tail[1:]
        else:
            return None
    else:
        if authority.count(":") > 1:
            return None
        host, sep, port_text = authority.partition(":")
        had_colon = bool(sep)
    if not host:
        return None
    if port_text:
        if not port_text.isdigit():
            return None
        port = int(port_text)
        if port < 1 or port > 65535:
            return None
    elif had_colon:
        return None
    elif default_port is None:
        return None
    else:
        port = default_port
    try:
        canonical = _canonical_host(host)
    except ProxyJailError:
        return None
    return (canonical, port)


def _host_header_value(header: bytes) -> Optional[str]:
    """Return the single Host header value, or None when absent/duplicated."""
    found = None
    for line in header.split(b"\r\n")[1:]:
        name, _, value = line.partition(b":")
        if name.strip().lower() == b"host":
            if found is not None:
                return None
            found = value.strip().decode("latin-1", "replace")
    return found


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
        try:
            canonical = _canonical_host(host)
        except ProxyJailError:
            return False
        return canonical in self.allowed_hosts

    @property
    def blocked_hosts(self) -> tuple:
        return tuple(self._blocked_hosts)

    def _reject(self, client: socket.socket, note: str, host: str = "", code: int = 403) -> None:
        self.blocked_count += 1
        if host and host not in self._blocked_hosts:
            self._blocked_hosts.append(host)
            if len(self._blocked_hosts) > 64:
                del self._blocked_hosts[0]
        phrase = _STATUS_PHRASES.get(code, "Forbidden")
        response = ("HTTP/1.1 %d %s\r\nX-Noesis-Jail: %s\r\nContent-Length: 0\r\nConnection: close\r\n\r\n" % (code, phrase, note)).encode("ascii")
        try:
            client.sendall(response)
        finally:
            # Drain any pending inbound data before closing. A close with unread
            # data still in the receive buffer triggers a TCP reset, which would
            # hide the status code from the client (esp. on the header-cap paths
            # where the request body is large). Draining to empty lets close() go
            # cleanly so the peer receives the rejection.
            client.settimeout(0.25)
            try:
                while True:
                    if not client.recv(65536):
                        break
            except Exception:
                pass
            try:
                client.close()
            except OSError:
                pass

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
            while b"\r\n\r\n" not in header:
                if len(header) >= MAX_HEADER:
                    return self._reject(client, "header_too_large", "<malformed>", code=431)
                chunk = client.recv(4096)
                if not chunk:
                    client.close()
                    return
                header += chunk
                if len(header) > MAX_FIRST_LINE and b"\r\n" not in header:
                    return self._reject(client, "first_line_too_long", "<malformed>", code=431)
            first_line_bytes = header.split(b"\r\n", 1)[0]
            if len(first_line_bytes) > MAX_FIRST_LINE:
                return self._reject(client, "first_line_too_long", "<malformed>", code=431)
            first_line = first_line_bytes.decode("latin-1", "replace")
            parts = first_line.split(" ")
            if len(parts) >= 2 and parts[0].upper() == "CONNECT":
                parsed = _split_authority(parts[1], default_port=None)
                if parsed is None:
                    return self._reject(client, "malformed_connect_authority", "<malformed>", code=400)
                host, port = parsed
                if not self._is_allowed(host):
                    return self._reject(client, "host_not_allowlisted", host)
                try:
                    upstream = self._open_upstream(host, port)
                except OSError as exc:
                    return self._reject(client, "upstream_error:%s" % type(exc).__name__, host, code=502)
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
                parsed = _split_authority(authority, default_port=80)
                if parsed is None:
                    return self._reject(client, "malformed_http_authority", "<malformed>", code=400)
                host, port = parsed
                host_value = _host_header_value(header)
                if host_value is None:
                    return self._reject(client, "split_brain_host", host, code=400)
                host_parsed = _split_authority(host_value, default_port=80)
                if host_parsed is None or host_parsed != (host, port):
                    return self._reject(client, "split_brain_host", host, code=400)
                if not self._is_allowed(host):
                    return self._reject(client, "host_not_allowlisted", host)
                try:
                    upstream = self._open_upstream(host, port)
                except OSError as exc:
                    return self._reject(client, "upstream_error:%s" % type(exc).__name__, host, code=502)
                self.allowed_count += 1
                rebuilt = (" ".join([parts[0], "/" + path_query] + parts[2:]) + "\r\n").encode("latin-1")
                upstream.sendall(rebuilt + header.split(b"\r\n", 1)[1])
                client.settimeout(None)
                upstream.settimeout(None)
                self._tunnel(client, upstream)
                return
            self._reject(client, "unsupported_request_shape", "<malformed>")
        except Exception:
            self.blocked_count += 1
            try:
                client.close()
            except OSError:
                pass


__all__ = ["AllowlistProxy", "ProxyJailError"]