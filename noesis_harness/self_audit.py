"""noesis_harness/self_audit.py

Read-only control-plane self-audit for the local-first Agent OS.

Patterns adapted from:
  - LoopX (state_projection integrity / replay-determinism checks)
  - agentmemory (leases.ts: TTL + one-holder invariants)
  - deepseek-harness (append-only session integrity)
  - Hermes (operator snapshot read-only projection discipline)

The auditor NEVER writes to the event log, the lease store, or any state file.
It only reads and reports. In this design new facts are always new events, so
the audit is deliberately side-effect free: it discovers drift, it does not
repair. A follow-up control-plane action may append a remediation event, but
self_audit itself stays append-only safe.

Design goals:
  - Deterministic: identical inputs always produce identical findings + digest.
  - Honest: every finding carries a severity and an evidence pointer
    (event_id / seq / task_key) so an operator can locate the drift.
  - Fail-closed: an unreadable or ambiguous record is reported, never skipped.
  - Idempotency-aware: it recognizes benign idempotent re-sends versus true
    content conflicts, so legitimate double-sends are not flagged as errors.

Zero dependencies (stdlib only).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional


# Severity ladder. Only ERROR / CRITICAL make a report not "ok".
SEVERITY_OK = "ok"
SEVERITY_INFO = "info"
SEVERITY_WARN = "warn"
SEVERITY_ERROR = "error"
SEVERITY_CRITICAL = "critical"

_FAILING = (SEVERITY_ERROR, SEVERITY_CRITICAL)


# Finding codes (stable machine-readable identifiers for tests + receipts).
CODE_SCOPE_MISSING = "scope_missing"
CODE_LOG_NOT_OBJECT = "event_log_record_not_object"
CODE_LOG_CORRUPT_NON_TAIL = "event_log_corrupt_non_tail"
CODE_LOG_TAIL_CORRUPTION = "event_log_tail_corruption"
CODE_EVENT_ID_CONFLICT = "event_id_conflict"
CODE_IDEMPOTENT_DUPLICATE = "idempotent_duplicate_event_id"
CODE_CONTENT_DUPLICATE = "content_duplicate_redundant"
CODE_SEQ_NOT_MONOTONIC = "event_seq_not_monotonic"
CODE_SEQ_GAP = "event_seq_gap"
CODE_LEASE_EXPIRED_ACTIVE = "lease_expired_active"
CODE_LEASE_HOLDER_OVERLAP = "lease_holder_overlap"
CODE_LEASE_TABLE_MISSING = "lease_table_missing"


def _fingerprint(event_type, payload):
    """Stable content hash, kept in sync with event_store._fingerprint."""
    canon = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(("%s\x00%s" % (event_type, canon)).encode("utf-8")).hexdigest()


class AuditReport:
    """Immutable-ish audit result with a deterministic sha256 digest."""

    def __init__(self, scope, findings):
        # type: (str, List[Dict[str, Any]]) -> None
        self.scope = scope
        self.findings = list(findings)

    @property
    def ok(self):
        # type: () -> bool
        return not any(f.get("severity") in _FAILING for f in self.findings)

    def digest(self):
        # type: () -> str
        ordered = sorted(
            self.findings,
            key=lambda f: (str(f.get("code", "")), str(f.get("seq", "")), str(f.get("evidence", ""))),
        )
        canon = json.dumps(ordered, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(canon.encode("utf-8")).hexdigest()

    def counts(self):
        # type: () -> Dict[str, int]
        out = {SEVERITY_INFO: 0, SEVERITY_WARN: 0, SEVERITY_ERROR: 0, SEVERITY_CRITICAL: 0}
        for f in self.findings:
            sev = f.get("severity")
            if sev in out:
                out[sev] += 1
        return out

    def as_dict(self):
        # type: () -> Dict[str, Any]
        return {
            "scope": self.scope,
            "ok": self.ok,
            "digest": self.digest(),
            "counts": self.counts(),
            "findings": self.findings,
        }

    def as_json(self):
        # type: () -> str
        return json.dumps(self.as_dict(), ensure_ascii=False, sort_keys=True, indent=2)


def _finding(code, severity, message, evidence=None, seq=None):
    # type: (str, str, str, Optional[str], Optional[int]) -> Dict[str, Any]
    f = {"code": code, "severity": severity, "message": message}  # type: Dict[str, Any]
    if evidence is not None:
        f["evidence"] = evidence
    if seq is not None:
        f["seq"] = seq
    return f


def _read_text_lines(path):
    # type: (str) -> List[str]
    with open(path, "rb") as fh:
        raw = fh.read()
    return [line.decode("utf-8") for line in raw.splitlines()]


def audit_event_store(path, scope="event_store"):
    # type: (str, str) -> AuditReport
    """Read-only integrity audit of an append-only JSONL event log.

    Detects: missing file, non-object records, non-tail corruption (fatal),
    tail corruption (data-loss risk, info), event_id conflicts, benign
    idempotent duplicates, redundant content duplicates (two ids, one payload),
    non-monotonic sequence numbers and sequence gaps.
    """
    findings = []  # type: List[Dict[str, Any]]
    if not os.path.exists(path):
        findings.append(_finding(CODE_SCOPE_MISSING, SEVERITY_INFO,
                                  "event log not present; nothing to audit", evidence=path))
        return AuditReport(scope, findings)

    try:
        lines = _read_text_lines(path)
    except (OSError, UnicodeDecodeError) as exc:
        findings.append(_finding(CODE_LOG_CORRUPT_NON_TAIL, SEVERITY_CRITICAL,
                                  "event log unreadable: %s" % exc, evidence=path))
        return AuditReport(scope, findings)

    non_empty = [(i, text) for i, text in enumerate(lines) if text.strip()]
    last_index = non_empty[-1][0] if non_empty else -1

    seen_ids = {}  # type: Dict[str, str]
    seen_fp = {}  # type: Dict[str, str]
    prev_seq = None  # type: Optional[int]

    for index, text in non_empty:
        is_tail = index == last_index
        try:
            rec = json.loads(text)
        except (ValueError, TypeError):
            if is_tail:
                findings.append(_finding(CODE_LOG_TAIL_CORRUPTION, SEVERITY_INFO,
                                         "trailing line unparseable; replay would truncate it (possible last-write loss)",
                                         evidence=path, seq=index))
            else:
                findings.append(_finding(CODE_LOG_CORRUPT_NON_TAIL, SEVERITY_CRITICAL,
                                         "non-tail line unparseable; log cannot be replayed safely",
                                         evidence=path, seq=index))
            continue

        if not isinstance(rec, dict):
            sev = SEVERITY_CRITICAL if not is_tail else SEVERITY_ERROR
            findings.append(_finding(CODE_LOG_NOT_OBJECT, sev,
                                     "event record is not a JSON object", evidence=path, seq=index))
            continue

        event_id = str(rec.get("event_id", ""))
        event_type = str(rec.get("type", ""))
        fp = _fingerprint(event_type, rec.get("payload"))
        seq = rec.get("seq")

        prior_fp = seen_ids.get(event_id)
        if prior_fp is not None:
            if prior_fp == fp:
                findings.append(_finding(CODE_IDEMPOTENT_DUPLICATE, SEVERITY_INFO,
                                         "benign idempotent re-send of event_id",
                                         evidence=event_id, seq=seq))
            else:
                findings.append(_finding(CODE_EVENT_ID_CONFLICT, SEVERITY_ERROR,
                                         "event_id reused with different content (tamper / replay break)",
                                         evidence=event_id, seq=seq))
        seen_ids[event_id] = fp

        first_id = seen_fp.get(fp)
        if first_id is not None and first_id != event_id:
            findings.append(_finding(CODE_CONTENT_DUPLICATE, SEVERITY_WARN,
                                     "same content fingerprint written under two event_ids (redundant write)",
                                     evidence="%s|%s" % (first_id, event_id), seq=seq))
        seen_fp[fp] = event_id

        if isinstance(seq, int):
            if prev_seq is not None and seq <= prev_seq:
                findings.append(_finding(CODE_SEQ_NOT_MONOTONIC, SEVERITY_ERROR,
                                         "sequence number not strictly increasing (%s after %s)" % (seq, prev_seq),
                                         evidence=event_id, seq=seq))
            elif prev_seq is not None and seq > prev_seq + 1:
                findings.append(_finding(CODE_SEQ_GAP, SEVERITY_WARN,
                                         "sequence gap (jumped %s -> %s)" % (prev_seq, seq),
                                         evidence=event_id, seq=seq))
            prev_seq = seq

    return AuditReport(scope, findings)


def audit_coordination(db_path, now=None, scope="coordination"):
    # type: (str, Optional[float], str) -> AuditReport
    """Read-only integrity audit of the SQLite lease/coordination store.

    Checks: missing db, missing leases table, active leases whose TTL has
    expired (relative to `now`, defaulting to the latest acquired_at so the
    result is deterministic given the data), and holders that own more than one
    active lease (a one-lease-per-holder invariant violation).
    """
    findings = []  # type: List[Dict[str, Any]]
    if not os.path.exists(db_path):
        findings.append(_finding(CODE_SCOPE_MISSING, SEVERITY_INFO,
                                  "coordination store not present; nothing to audit", evidence=db_path))
        return AuditReport(scope, findings)

    try:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "leases" not in tables:
            conn.close()
            findings.append(_finding(CODE_LEASE_TABLE_MISSING, SEVERITY_INFO,
                                      "leases table absent; coordination unused", evidence=db_path))
            return AuditReport(scope, findings)
        rows = [dict(r) for r in conn.execute(
            "SELECT task_key, holder, acquired_at, expires_at, status FROM leases")]
        conn.close()
    except sqlite3.Error as exc:
        findings.append(_finding(CODE_LEASE_TABLE_MISSING, SEVERITY_CRITICAL,
                                  "coordination store unreadable: %s" % exc, evidence=db_path))
        return AuditReport(scope, findings)

    if now is None:
        now = max((float(r.get("acquired_at") or 0) for r in rows), default=0.0)

    holder_active = {}  # type: Dict[str, List[str]]
    for r in rows:
        status = str(r.get("status", ""))
        if status != "active":
            continue
        holder = str(r.get("holder", ""))
        task_key = str(r.get("task_key", ""))
        holder_active.setdefault(holder, []).append(task_key)
        expires_at = r.get("expires_at")
        if isinstance(expires_at, (int, float)) and float(expires_at) <= now:
            findings.append(_finding(CODE_LEASE_EXPIRED_ACTIVE, SEVERITY_WARN,
                                     "active lease past TTL (holder=%s)" % holder,
                                     evidence=task_key))

    for holder, keys in holder_active.items():
        if len(keys) > 1:
            findings.append(_finding(CODE_LEASE_HOLDER_OVERLAP, SEVERITY_WARN,
                                     "holder owns %d active leases (one-lease-per-holder violated)" % len(keys),
                                     evidence=holder))

    return AuditReport(scope, findings)


def run_self_audit(events_path=None, leases_path=None, now=None):
    # type: (Optional[str], Optional[str], Optional[float]) -> AuditReport
    """Combined control-plane audit across every supplied store.

    Returns a single merged report whose `ok` is False if any sub-scope fails.
    The merged digest is deterministic given the inputs and finding order.
    """
    reports = []  # type: List[AuditReport]
    if events_path:
        reports.append(audit_event_store(events_path))
    if leases_path:
        reports.append(audit_coordination(leases_path, now=now))

    merged = []  # type: List[Dict[str, Any]]
    for rep in reports:
        for f in rep.findings:
            tagged = dict(f)
            tagged["scope"] = rep.scope
            merged.append(tagged)
    return AuditReport("control_plane", merged)


def main(argv=None):
    # type: (Optional[List[str]]) -> int
    import argparse

    p = argparse.ArgumentParser(description="NOESIS control-plane self-audit (read-only)")
    p.add_argument("--events", action="append", default=[],
                   help="path to an append-only event log (JSONL); repeatable")
    p.add_argument("--leases", action="append", default=[],
                   help="path to a SQLite coordination store; repeatable")
    p.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    p.add_argument("--strict", action="store_true",
                   help="exit non-zero if any error/critical finding is present")
    p.add_argument("--now", type=float, default=None,
                   help="override 'now' for lease TTL checks (deterministic replay)")
    args = p.parse_args(argv)

    reports = []  # type: List[AuditReport]
    for path in args.events:
        reports.append(audit_event_store(path))
    for path in args.leases:
        reports.append(audit_coordination(path, now=args.now))

    if not reports:
        reports.append(AuditReport("control_plane", [_finding(
            CODE_SCOPE_MISSING, SEVERITY_INFO, "no stores supplied to audit")]))

    merged = run_self_audit(
        events_path=(args.events[0] if args.events else None),
        leases_path=(args.leases[0] if args.leases else None),
        now=args.now,
    )
    # Re-merge all supplied stores (run_self_audit only takes one of each).
    all_findings = []  # type: List[Dict[str, Any]]
    for rep in reports:
        for f in rep.findings:
            tagged = dict(f)
            tagged["scope"] = rep.scope
            all_findings.append(tagged)
    merged = AuditReport("control_plane", all_findings)

    if args.json:
        print(merged.as_json())
    else:
        print("NOESIS control-plane self-audit")
        print("  scope: %s" % merged.scope)
        print("  ok:    %s" % merged.ok)
        counts = merged.counts()
        print("  info/warn/error/critical: %d/%d/%d/%d" % (
            counts[SEVERITY_INFO], counts[SEVERITY_WARN],
            counts[SEVERITY_ERROR], counts[SEVERITY_CRITICAL]))
        print("  digest: %s" % merged.digest())
        for f in merged.findings:
            loc = f.get("scope", "")
            if f.get("evidence") is not None:
                loc += "[%s]" % f.get("evidence")
            print("  - %-7s %-32s %s" % (f.get("severity"), f.get("code"), loc))

    return 1 if (args.strict and not merged.ok) else 0


if __name__ == "__main__":
    raise SystemExit(main())
