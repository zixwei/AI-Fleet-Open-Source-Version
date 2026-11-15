"""Smoke test for the Stage 0 prototype (deliverable #1).

Covers the core flow end to end, using FastAPI's TestClient (no server
needed): register -> approve -> create task -> send message -> duplicate
delivery is a no-op -> status transitions -> audit chain verifies.

Run:  python -m pytest tests/test_smoke.py -q
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

os.environ["AI_FLEET_DB"] = "sqlite:////tmp/ai_fleet_smoke.db"
os.environ["AI_FLEET_API_KEY"] = "smoke-test-key"

from app.main import app  # noqa: E402

HEADERS = {"X-API-Key": "smoke-test-key"}


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    db_path = tmp_path / "smoke.db"
    monkeypatch.setenv("AI_FLEET_DB", f"sqlite:///{db_path}")
    import app.config as config

    config.DATABASE_PATH = str(db_path)
    from app import storage as db

    db.init_db()
    yield


def test_core_flow():
    client = TestClient(app)

    assert client.get("/health").json()["status"] == "ok"

    # 1. Register an agent (Pending), then approve it.
    r = client.post(
        "/agents",
        json={"agent_id": "agent-a", "name": "Agent A", "endpoint": "http://a.local", "capabilities": ["review"]},
        headers=HEADERS,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "Pending"
    r = client.post("/agents/agent-a/approve", headers=HEADERS)
    assert r.json()["status"] == "Active"

    # 2. Create a task for the Active agent.
    r = client.post("/tasks", json={"agent_id": "agent-a", "title": "review the plan"}, headers=HEADERS)
    assert r.status_code == 200, r.text
    task_id = r.json()["task_id"]
    assert r.json()["status"] == "submitted"

    # 3. Send a message; then replay the identical envelope: no duplicate.
    r = client.post(
        f"/tasks/{task_id}/messages",
        json={"sender_agent_id": "agent-a", "event_type": "task.assigned", "payload": {"note": "go"}},
        headers=HEADERS,
    )
    assert r.status_code == 200, r.text
    assert r.json()["stored"] is True
    envelope = r.json()["message"]
    key = envelope["idempotency_key"]

    from app.messaging.bus import bus

    replay = bus.republish(envelope)
    assert replay["stored"] is False
    assert replay["message"]["idempotency_key"] == key
    assert len(client.get(f"/tasks/{task_id}/messages", headers=HEADERS).json()) == 1

    # 4. Status transitions; illegal transition is rejected.
    r = client.post(f"/tasks/{task_id}/status", json={"status": "working"}, headers=HEADERS)
    assert r.json()["status"] == "working"
    r = client.post(f"/tasks/{task_id}/status", json={"status": "submitted"}, headers=HEADERS)
    assert r.status_code == 400
    r = client.post(f"/tasks/{task_id}/status", json={"status": "completed"}, headers=HEADERS)
    assert r.json()["status"] == "completed"

    # 5. Audit log is append-only and the hash chain verifies.
    r = client.get("/audit/verify", headers=HEADERS)
    assert r.json()["ok"] is True
    assert r.json()["checked"] >= 5


def test_auth_required():
    client = TestClient(app)
    assert client.get("/agents").status_code == 401
    assert client.get("/agents", headers={"X-API-Key": "wrong"}).status_code == 401
