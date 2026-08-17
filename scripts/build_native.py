#!/usr/bin/env python3
"""Prepare or run native NOESIS packaging on a Python 3.14 target host."""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def verify_target(target: str) -> dict:
    actual = sys.platform
    normalized = "windows" if actual.startswith("win") else "macos" if actual == "darwin" else "linux"
    return {"python_ok": sys.version_info[:2] == (3, 14), "platform_ok": target == normalized, "actual_python": "%d.%d.%d" % sys.version_info[:3], "actual_platform": normalized, "architecture": platform.machine(), "target": target}


def command_for(backend: str, target: str) -> list[str]:
    if backend == "pyinstaller":
        return [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "packaging/noesis_portable.spec"]
    if backend == "briefcase":
        return [sys.executable, "-m", "briefcase", "package", target, "--no-input"]
    raise ValueError("backend must be pyinstaller or briefcase")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build NOESIS native artifact")
    parser.add_argument("--backend", choices=("pyinstaller", "briefcase"), required=True)
    parser.add_argument("--target", choices=("windows", "macos"), required=True)
    parser.add_argument("--run", action="store_true", help="run the native builder after all gates pass; default is dry-run")
    args = parser.parse_args(argv)
    report = verify_target(args.target)
    report["backend_available"] = shutil.which(args.backend) is not None or bool(importlib_available(args.backend))
    report["command"] = command_for(args.backend, args.target)
    report["dry_run"] = not args.run
    print(json.dumps(report, sort_keys=True))
    if not report["python_ok"] or not report["platform_ok"]:
        return 2
    if args.run:
        return subprocess.run(report["command"], check=False).returncode
    return 0


def importlib_available(module: str) -> bool:
    try:
        __import__(module)
    except ImportError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
