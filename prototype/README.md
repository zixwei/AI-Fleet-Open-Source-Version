# AI Fleet Hub — Stage 0 prototype (deliverable #1)

Runnable minimal technical prototype for the AI Fleet cross-vendor agent
collaboration platform (plan v0.2.6 §25 #1). Modular monolith (§4): six
logical modules as packages, one deployable process.

## What it does

- **Agent Registry** — manual registration, admin approval (Pending → Active).
- **Orchestration** — task lifecycle: submitted → working → completed / failed / cancelled. No silent task loss.
- **Message Bus** — unified envelope (plan v0.2.6) with platform idempotency
  keys (`tenant:sender:task:event:message`). A duplicate delivery is a no-op:
  no duplicate side effects (principle 5).
- **Audit log** — append-only, hash-chained. `/audit/verify` recomputes it.
- **Identity** — API key per tenant (Stage 0 placeholder; full auth in §7).

## Run (no Docker needed)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
AI_FLEET_API_KEY=dev-key-change-me .venv/bin/uvicorn app.main:app --port 8000
```

## Run (reference deployment, plan v0.2.6 §23)

```bash
docker compose up --build
```

This starts the API plus PostgreSQL 18.7 and Valkey 9.1.2 (pinned versions in
`docker-compose.yml`; frozen in `docs/ENVIRONMENT.md`). The prototype stores
data in SQLite and uses an in-process bus by default; the Postgres and Valkey
adapters are the next step, not yet wired.

## Try it

```bash
KEY=dev-key-change-me
curl -s localhost:8000/health
curl -s -X POST localhost:8000/agents -H "X-API-Key: $KEY" \
  -d '{"agent_id":"agent-a","name":"Agent A","endpoint":"http://a.local","capabilities":["review"]}'
curl -s -X POST localhost:8000/agents/agent-a/approve -H "X-API-Key: $KEY"
curl -s -X POST localhost:8000/tasks -H "X-API-Key: $KEY" \
  -d '{"agent_id":"agent-a","title":"review the plan"}'
# then POST /tasks/{id}/messages, GET /tasks/{id}, GET /audit/verify
```

## Test

```bash
.venv/bin/python -m pytest tests/test_smoke.py -q
```

## What is NOT claimed

- A2A / MCP compatibility is **not** implemented or verified here. That is
  deliverables #2 / #3 (wuse). This prototype must not be presented as
  A2A- or MCP-compatible.
- The Postgres / Valkey adapters are **not** wired yet; the reference
  deployment runs them, but the API still uses SQLite + in-process bus.
- No performance numbers are claimed; none are measured yet (plan §22).
