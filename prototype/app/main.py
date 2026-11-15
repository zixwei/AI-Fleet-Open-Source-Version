"""AI Fleet Hub - Core API (modular monolith, Stage 0 deliverable #1).

Endpoints (all except /health require X-API-Key):
  POST /agents              register an agent (manual registration, Pending)
  GET  /agents              list agents
  POST /agents/{id}/approve approve an agent (Pending -> Active)
  POST /agents/{id}/suspend suspend an agent
  POST /tasks               create a task for an Active agent
  GET  /tasks               list tasks
  GET  /tasks/{id}          get task status
  POST /tasks/{id}/status   move a task (submitted->working->completed/failed/cancelled)
  POST /tasks/{id}/messages send a message (idempotent on idempotency_key)
  GET  /tasks/{id}/messages list messages for a task
  GET  /audit               append-only audit log (hash-chained)
  GET  /audit/verify        verify the audit hash chain
  GET  /health              health check (no auth)

Run:  uvicorn app.main:app --host 127.0.0.1 --port 8000
"""
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app import config
from app.identity import require_api_key
from app import observability as audit
from app import registry
from app.messaging.bus import bus
from app import orchestration
from app import storage as db

app = FastAPI(title="AI Fleet Hub", version="0.1.0-stage0")


@app.on_event("startup")
def startup():
    db.init_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-fleet-hub", "version": "0.1.0-stage0"}


class AgentIn(BaseModel):
    agent_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)
    capabilities: list[str] = []


@app.post("/agents")
def create_agent(body: AgentIn, auth=Depends(require_api_key)):
    try:
        agent = registry.register_agent(body.agent_id, body.name, body.endpoint, body.capabilities)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    audit.record(auth["tenant_id"], "agent.register", body.agent_id, {"name": body.name})
    return agent


@app.get("/agents")
def list_agents(auth=Depends(require_api_key)):
    return registry.list_agents()


@app.post("/agents/{agent_id}/approve")
def approve_agent(agent_id: str, auth=Depends(require_api_key)):
    try:
        agent = registry.approve_agent(agent_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    audit.record(auth["tenant_id"], "agent.approve", agent_id, {})
    return agent


@app.post("/agents/{agent_id}/suspend")
def suspend_agent(agent_id: str, auth=Depends(require_api_key)):
    try:
        agent = registry.suspend_agent(agent_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    audit.record(auth["tenant_id"], "agent.suspend", agent_id, {})
    return agent


class TaskIn(BaseModel):
    agent_id: str = Field(min_length=1)
    title: str = Field(min_length=1)


@app.post("/tasks")
def create_task(body: TaskIn, auth=Depends(require_api_key)):
    try:
        task = orchestration.create_task(auth["tenant_id"], body.agent_id, body.title)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    audit.record(auth["tenant_id"], "task.create", task["task_id"], {"agent_id": body.agent_id})
    return task


@app.get("/tasks")
def list_tasks(auth=Depends(require_api_key)):
    return orchestration.list_tasks(auth["tenant_id"])


@app.get("/tasks/{task_id}")
def get_task(task_id: str, auth=Depends(require_api_key)):
    task = orchestration.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task


class StatusIn(BaseModel):
    status: str = Field(min_length=1)


@app.post("/tasks/{task_id}/status")
def set_task_status(task_id: str, body: StatusIn, auth=Depends(require_api_key)):
    try:
        task = orchestration.set_status(task_id, body.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    audit.record(auth["tenant_id"], "task.status", task_id, {"status": body.status})
    return task


class MessageIn(BaseModel):
    sender_agent_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    payload: dict = {}


@app.post("/tasks/{task_id}/messages")
def send_message(task_id: str, body: MessageIn, auth=Depends(require_api_key)):
    task = orchestration.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    result = bus.send(
        tenant_id=auth["tenant_id"],
        sender_agent_id=body.sender_agent_id,
        recipient_agent_id=task["agent_id"],
        task_id=task_id,
        event_type=body.event_type,
        payload=body.payload,
    )
    audit.record(
        auth["tenant_id"],
        "message.send" if result["stored"] else "message.duplicate",
        task_id,
        {"event_type": body.event_type, "stored": result["stored"]},
    )
    return {"stored": result["stored"], "message": result["message"]}


@app.get("/tasks/{task_id}/messages")
def list_messages(task_id: str, auth=Depends(require_api_key)):
    if not orchestration.get_task(task_id):
        raise HTTPException(status_code=404, detail="task not found")
    return bus.list_for_task(task_id)


@app.get("/audit")
def list_audit(limit: int = 100, auth=Depends(require_api_key)):
    return audit.list_audit(limit)


@app.get("/audit/verify")
def verify_audit(auth=Depends(require_api_key)):
    return audit.verify_chain()
