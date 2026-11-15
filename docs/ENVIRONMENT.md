# Stage 0 reference environment — frozen (plan v0.2.6 §23)

Frozen 2026-11-15 by Xuse (code lead) at Stage 0 start. §38 step 1: freeze
§23 versions before building deliverable #1. Any change to this file is a
scope change and needs owner approval (plan §24).

## Frozen versions

| Component | Pinned version | Released | Source / note |
|---|---|---|---|
| OS | Ubuntu 24.04 LTS (24.04.5) | 2024-04 | Verified on this host |
| CPU | 4 vCPU | — | Verified on this host |
| Memory | 16 GB (reference) | — | This dev host has 7 GB; see deviation below |
| Python | 3.12.3 | 2024-04 | Verified on this host |
| Docker Engine | 29.9.3 | 2026-11-03 | Current supported release (29.x line) |
| Docker Compose | v2 (plugin, bundled with Engine 29) | — | Standalone v1 is EOL |
| PostgreSQL | 18.7 | 2026-11-09 | Latest stable major; supported to 2030-11-14. v19 GA planned 2026-11-19, not yet released — do not pin it yet |
| Message queue | Valkey 9.1.2 | 2026-08-31 | BSD-licensed, wire-compatible with Redis; image `valkey/valkey:9.1.2-alpine` |
| FastAPI | 0.163.0 | — | Pinned in `prototype/requirements.txt` |
| Uvicorn | 0.54.0 | — | Pinned in `prototype/requirements.txt` |
| Pydantic | 2.14.3 | — | Pinned in `prototype/requirements.txt` |

## Why Valkey, not Redis

Redis 8.x is published under RSALv2 / SSPLv1 / AGPLv3 (tri-license); RSALv2
and SSPLv1 are not open-source licences. This project is Apache 2.0, so the
queue is Valkey (BSD, the open-source continuation of Redis). Valkey speaks
the same protocol, so Redis 8.10.3 (2026-10-26) remains a drop-in alternative
if the team ever decides otherwise.

## Deviations from the §23 reference (recorded, not hidden)

1. **This dev host has 7 GB RAM, not 16 GB.** The reference stays 16 GB;
   performance numbers from this host must not be mixed with reference-env
   numbers (plan §23).
2. **No Docker on this host.** The prototype runs directly on Python +
   SQLite + in-process bus here. The reference deployment (`docker-compose.yml`)
   is provided but not yet executed on this host; it will be verified when a
   Docker host is available (gate 07).
3. **PostgreSQL / Valkey adapters not yet wired.** The API still uses SQLite
   + in-process bus. The compose file runs Postgres 18.7 and Valkey 9.1.2, but
   the code does not connect to them yet. Wiring them is the next step of
   deliverable #1.

## Network and time

- Isolated test network (per §23); no production traffic on it.
- Time: UTC internally, converted to ET for display (per §23).
