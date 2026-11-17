#!/usr/bin/env python3
"""Frozen-app entrypoint for NOESIS portable control plane."""
from noesis_harness.portable_launcher import main

if __name__ == "__main__":
    raise SystemExit(main())
