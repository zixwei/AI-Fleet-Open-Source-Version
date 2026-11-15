"""Module 6 - Observability (audit log).

Append-only log with a hash chain (plan v0.2.6): each entry records the hash
of the previous entry, so tampering with history breaks the chain. A hash
chain alone is not tamper-proof; it is evidence, not a guarantee.
"""
import hashlib
import json

from app import storage as db
from app.messaging import now_iso


def _entry_hash(prev_hash, created_at, actor, action, target, detail) -> str:
    raw = "|".join(
        [prev_hash, created_at, actor, action, target, json.dumps(detail, sort_keys=True)]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def record(actor: str, action: str, target: str, detail: dict | None = None) -> dict:
    detail = detail or {}
    created_at = now_iso()
    prev_hash = db.last_audit_hash()
    entry_hash = _entry_hash(prev_hash, created_at, actor, action, target, detail)
    seq = db.append_audit(prev_hash, entry_hash, created_at, actor, action, target, detail)
    return {
        "seq": seq,
        "prev_hash": prev_hash,
        "entry_hash": entry_hash,
        "created_at": created_at,
        "actor": actor,
        "action": action,
        "target": target,
        "detail": detail,
    }


def list_audit(limit: int = 100, actor: str | None = None) -> list:
    """List audit entries, newest first. When actor is given, only that
    tenant's entries are returned (T08: no cross-tenant audit reads)."""
    return db.list_audit(limit=limit, actor=actor)


def verify_chain(limit: int = 1000) -> dict:
    """Recompute the chain over the most recent entries. Returns ok/False
    plus the first broken sequence, if any."""
    entries = db.list_audit(limit=limit)
    entries = list(reversed(entries))  # oldest first
    prev = "GENESIS"
    for e in entries:
        if e["prev_hash"] != prev:
            return {"ok": False, "broken_at_seq": e["seq"]}
        recomputed = _entry_hash(
            e["prev_hash"], e["created_at"], e["actor"], e["action"], e["target"], e["detail"]
        )
        if recomputed != e["entry_hash"]:
            return {"ok": False, "broken_at_seq": e["seq"]}
        prev = e["entry_hash"]
    return {"ok": True, "checked": len(entries)}
