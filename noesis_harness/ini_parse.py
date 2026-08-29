"""noesis_harness/ini_parse.py — minimal INI parse.

Patterns: LoopX ini.
Stdlib only.
"""
from __future__ import annotations
import configparser, io

def parse(text: str) -> dict:
    p=configparser.ConfigParser(); p.read_string(text); return {s: dict(p[s]) for s in p.sections()}
def get(d: dict, section: str, key: str, default=None): return d.get(section, {}).get(key, default)
