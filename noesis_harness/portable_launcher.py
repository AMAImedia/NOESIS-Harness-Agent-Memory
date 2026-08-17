"""Portable launch boundary for Windows/macOS NOESIS distributions.

Patterns are borrowed from portable application layouts, Windows command
launchers, NOESIS user-data separation, and the read-only control plane. The
launcher starts only the local HealthServer; it does not install packages,
invoke models, execute skill entrypoints, or require Node/npm.
"""

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Tuple

from .health_server import HealthServer
from .provider_registry import ProviderRegistry
from .user_data import user_data_paths


class PortableLaunchError(ValueError):
    """Raised when portable install/data boundaries are unsafe."""


@dataclass(frozen=True)
class PortableLayout:
    install_root: Path
    data_root: Path
    runtime_root: Path
    logs_root: Path

    def ensure(self) -> "PortableLayout":
        for path in (self.install_root, self.data_root, self.runtime_root, self.logs_root):
            path.mkdir(parents=True, exist_ok=True)
        return self


def resolve_layout(install_root: str, data_root: Optional[str] = None, env: Optional[Mapping[str, str]] = None, platform: Optional[str] = None, home: Optional[str] = None) -> PortableLayout:
    install = Path(install_root).expanduser().resolve()
    if not install.is_dir() and install.exists():
        raise PortableLaunchError("install_root must be a directory")
    environment = dict(os.environ if env is None else env)
    selected = data_root or environment.get("NOESIS_HOME")
    if selected:
        data = Path(selected).expanduser().resolve()
    elif platform in {"darwin", "win32"}:
        data = user_data_paths(env=environment, platform=platform, home=home, create=False).root
    else:
        data = install / "data"
    if data == install or install in data.parents:
        # install/data is permitted for a self-contained USB layout; code and data remain separate.
        if data == install:
            raise PortableLaunchError("data_root must be separate from install_root")
    runtime = data / "runtime"
    logs = data / "logs"
    return PortableLayout(install, data, runtime, logs)


def startup_probe(layout: PortableLayout, *, host: str = "127.0.0.1", port: int = 0) -> Tuple[str, int]:
    """Start/stop a read-only server and verify the persistent data boundary."""
    layout.ensure()
    sentinel = layout.data_root / "state" / "portable-startup.sentinel"
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text("noesis-portable-started\n", encoding="utf-8")
    with HealthServer(host=host, port=port, provider_registry=ProviderRegistry()) as server:
        address = server.address
    if not sentinel.is_file() or sentinel.read_text(encoding="utf-8") != "noesis-portable-started\n":
        raise PortableLaunchError("data-preservation sentinel missing")
    return address


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run NOESIS portable read-only control plane")
    parser.add_argument("--install-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    layout = resolve_layout(args.install_root, args.data_root)
    layout.ensure()
    server = HealthServer(host=args.host, port=args.port, provider_registry=ProviderRegistry())
    server.start()
    print("NOESIS portable control plane listening at http://%s:%d" % server.address, flush=True)
    print("Install root: %s" % layout.install_root, flush=True)
    print("Data root: %s" % layout.data_root, flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    finally:
        server.stop()


__all__ = ["PortableLayout", "PortableLaunchError", "resolve_layout", "startup_probe", "main"]
