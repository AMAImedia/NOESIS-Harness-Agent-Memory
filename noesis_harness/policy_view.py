"""Read-only policy projection for the NOESIS harness.

Patterns borrowed from:
- Cloudflare-OS: read-only policy manifest model used to declare and inspect
  access/behavior rules without mutating harness state.
- agentmemory: stable, content-addressed snapshot digests so a view can be
  fingerprinted and compared deterministically across runs.

This module is pure and side-effect free. It only reads a policy JSON file
(a list of rule objects) and projects it into an immutable-shaped view. It
uses just the Python standard library (hashlib, json) so it can be imported on
dependency-free paths inside the harness.
"""

import hashlib
import json


def _read_policy(path):
    """Read and parse a policy JSON file.

    Returns the parsed object. Raises the underlying ``OSError`` or
    ``json.JSONDecodeError`` if the file is missing or malformed.
    """
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_rules(policy):
    """Normalize a policy object into a sorted list of rule dicts.

    Accepts either a mapping with a ``rules`` key (list of dicts) or a bare
    list of rule dicts. Each rule is projected to ``{"id": str, "enabled":
    bool, "raw": <original dict>}``. Rules are sorted by ``id`` so the
    resulting view is order-independent and deterministic. A rule missing an
    ``id`` is rejected with ``ValueError`` because ids are required to make a
    stable, comparable projection.
    """
    raw = policy
    if isinstance(policy, dict):
        raw = policy.get("rules", [])

    if not isinstance(raw, list):
        raise ValueError("policy must contain a list of rules")

    rules = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("each rule must be an object")
        rule_id = item.get("id")
        if rule_id is None:
            raise ValueError("rule entry missing 'id'")
        enabled = bool(item.get("enabled", True))
        rules.append({"id": str(rule_id), "enabled": enabled, "raw": item})

    rules.sort(key=lambda rule: rule["id"])
    return rules


def _digest(rules):
    """Compute a stable SHA-256 hex digest over the normalized rules.

    Only ``id`` and ``enabled`` contribute to the digest so that unrelated
    metadata changes do not alter the policy fingerprint. The contribution is
    order-independent because the rules are already sorted by id.
    """
    slim = [{"id": rule["id"], "enabled": rule["enabled"]} for rule in rules]
    canonical = json.dumps(
        slim,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def view(path):
    """Load a policy JSON file and return a read-only view dict.

    The returned dict has the shape::

        {
            "path": <source path>,
            "rules": [{"id": str, "enabled": bool, "raw": dict}, ...],
            "count": <int>,
            "enabled_count": <int>,
            "digest": <sha256 hex>,
        }

    ``rules`` is sorted by id, making the view deterministic regardless of
    manifest ordering. The ``digest`` is a stable content fingerprint of the
    rule set (id + enabled flags only).
    """
    policy = _read_policy(path)
    rules = _normalize_rules(policy)
    enabled_count = sum(1 for rule in rules if rule["enabled"])
    return {
        "path": path,
        "rules": rules,
        "count": len(rules),
        "enabled_count": enabled_count,
        "digest": _digest(rules),
    }


def filter_enabled(view):
    """Return the list of enabled rule ids in ``view``.

    ``view`` is a dict as produced by :func:`view`. The returned ids are
    ordered by the (already sorted) rule list.
    """
    return [
        rule["id"]
        for rule in view.get("rules", [])
        if rule.get("enabled")
    ]
