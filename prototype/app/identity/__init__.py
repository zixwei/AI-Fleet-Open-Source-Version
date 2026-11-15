"""Module 1 - Identity & Authorization (minimal, Stage 0).

Stage 0 uses one API key per tenant (header X-API-Key). This is a
placeholder for the full auth model (plan v0.2.6 §7): per-agent credentials,
scoped tokens, and human approval for high-risk ops. No raw credentials are
ever shared between agents (principle 3).

Multi-tenant keys: set AI_FLEET_TENANT_API_KEYS to a JSON object mapping
API key -> tenant id, e.g. {"key-a": "tenant-a", "key-b": "tenant-b"}.
When set, each key resolves to its own tenant; a key not in the map is
rejected. When unset, the single AI_FLEET_API_KEY maps to DEFAULT_TENANT.
"""
import json
import os

from fastapi import Header, HTTPException

from app import config


def _tenant_key_map() -> dict:
    raw = os.environ.get("AI_FLEET_TENANT_API_KEYS", "")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def require_api_key(x_api_key: str | None = Header(default=None)):
    key_map = _tenant_key_map()
    if key_map:
        tenant_id = key_map.get(x_api_key)
        if tenant_id is None:
            raise HTTPException(status_code=401, detail="invalid or missing API key")
        return {"tenant_id": tenant_id}
    if x_api_key != config.API_KEY:
        raise HTTPException(status_code=401, detail="invalid or missing API key")
    return {"tenant_id": config.DEFAULT_TENANT}
