"""Module 1 - Identity & Authorization (minimal, Stage 0).

Stage 0 uses a single API key per tenant (header X-API-Key). This is a
placeholder for the full auth model (plan v0.2.6 §7): per-agent credentials,
scoped tokens, and human approval for high-risk ops. No raw credentials are
ever shared between agents (principle 3).
"""
from fastapi import Header, HTTPException

from app import config


def require_api_key(x_api_key: str | None = Header(default=None)):
    if x_api_key != config.API_KEY:
        raise HTTPException(status_code=401, detail="invalid or missing API key")
    return {"tenant_id": config.DEFAULT_TENANT}
