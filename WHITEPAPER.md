# AI Fleet — Cross-Vendor Agent Collaboration Platform

## Whitepaper

**Version:** 1.0 (based on plan v0.2.6)
**Date:** 2026-11-14
**Status:** Stage 0 (technical validation) approved and in progress
**License (proposed):** Apache License 2.0 (to be confirmed)
**Repository:** https://github.com/zixwei/AI-Fleet-Open-Source-Version

---

## 1. Vision

Build an open-source, self-hostable platform where agents from different vendors, models, and runtimes can discover each other, establish trusted identities, exchange messages securely, delegate tasks, track execution, hand over files and artifacts, and be audited — forming an organized AI collaboration team.

The real success criterion is not connecting many model APIs. It is this:

> **Agents from different sources can complete cross-vendor collaboration tasks securely, reliably, and repeatably — without sharing raw account credentials.**

## 2. The Problem

Today's agents are siloed:

- **No common communication.** Agents from different vendors lack a unified, reliable way to talk to each other.
- **No discovery.** One agent cannot easily find another agent's capabilities.
- **No delegation protocol.** Task delegation, status sync, and result handover have no shared mechanism.
- **No shared context.** Work context, files, results, and decision records cannot move between vendors.
- **No unified trust.** Identity, permissions, security, and audit are fragmented per vendor.

The result is that multi-agent work is either confined to one vendor's ecosystem or glued together with ad-hoc scripts that break silently.

## 3. Design Principles

1. **Use open standards; do not reinvent the wire protocol.** Agent-to-agent collaboration uses **A2A**; tool and data access uses **MCP**. A connector layer adapts vendor API differences behind one internal message, event, and task model.
2. **A model API is not an agent.** Being able to call a model does not mean that vendor's agent collaboration is achieved. Only agents that pass the matching protocol and conformance tests enter the official compatibility list.
3. **Never share raw credentials.** Agents never exchange original account credentials. Identity is established by verifiable credentials and signatures, not by passing passwords or tokens around.
4. **Verification over assertion.** Protocol compatibility, capability claims, and artifact delivery are verified by tests and evidence — never asserted in documentation alone.
5. **Security from the MVP, not after it.** Identity, least privilege, sandboxing, audit, and human approval for sensitive operations are designed in from day one.
6. **Reliability is explicit.** The platform promises at-least-once delivery plus receiver-side idempotency. It does **not** promise end-to-end exactly-once delivery, and it never silently drops a task.
7. **Modular monolith first.** Logical modules are not microservices. Stage 0 ships a modular monolith (or a small number of processes) and splits only when a measured trigger is met: independent scaling becomes necessary, fault isolation cannot be satisfied, security boundaries differ, release cycles conflict in substance, or measured performance proves the current deployment is the bottleneck.

## 4. Architecture

### 4.1 Six logical modules

| Module | Responsibilities |
|---|---|
| Identity & Authorization | Agent identity, authentication, authorization, secret management |
| Fleet Control Plane | Agent registry, discovery, lifecycle, configuration, permissions |
| Orchestration Layer | Task creation, assignment, delegation, status tracking, failure handling, timeout, cancellation, recovery |
| Communication Infrastructure | Message delivery, queueing, retry, idempotency, webhooks, events, tracing |
| Storage & Workspace | Agent data, task data, artifacts, file storage, message records, audit records |
| Observability | Logs, metrics, distributed tracing, security events, cost statistics, alerts, diagnostics |

### 4.2 Deployment mapping (Stage 0)

- Identity & Authorization → identity module inside the Core API (database, secret manager)
- Fleet Control Plane → Agent Registry module inside the Core API (database)
- Orchestration → task orchestration module inside the Core API (database, message queue)
- Communication Infrastructure → standalone worker / message bus (message queue, external agents)
- Storage & Workspace → database and object storage
- Observability → standalone monitoring and logging components

### 4.3 Agent tiers

| Tier | Definition | Position |
|---|---|---|
| Tier 0 | Platform-native agents | Fully supported |
| Tier 1 | Open-protocol agents (A2A and other open agent protocols) | Core interop target |
| Tier 2a | Model APIs | Capability supplement |
| Tier 2b | Third-party hosted agent APIs | Extended access |
| Tier 3 | UI automation | Not in MVP |

Tier 3 must be labeled with its limits (lower stability, page changes can break the connection, real-time two-way communication hard to guarantee) and must never share a compatibility grade with native API access. Closed platforms with no public API, no authorization, or no permitted automation are not promised as supported.

## 5. Protocol Baselines

### 5.1 A2A — agent-to-agent communication

- Baseline: **A2A v1.0.1**. Version negotiation uses Major.Minor (`1.0`); the patch version `1.0.1` must not be placed in `A2A-Version`.
- Core operations: Send Message, Send Streaming Message, Get Task, Cancel Task, List Tasks, Subscribe to Task, Push Notification Configuration management.
- SDK method names, parameters, and behavior follow the official specification and the actual SDK for the corresponding version.
- Duplicate-notification idempotency in A2A uses SHOULD semantics: the receiver implements idempotent handling but must not escalate SHOULD to MUST.

### 5.2 MCP — tool and context access

- Baseline: the **2026-07-28 revision**.
- Design: stateless core, explicit state handles, Tasks extension, explicit version compatibility, explicit connection lifecycle.
- Legacy stateful implementations must not be mixed directly into new adapters.

### 5.3 Discovery and Agent Card verification

Discovery is: manual registration → administrator approval → Agent Card fetched from an authorized source → source and identity verified → capability claims verified → periodic re-fetch → change detection → trust revoked when necessary. The central registry is a platform feature; it must not be presented as an A2A-native requirement.

An Agent Card does not automatically mean a trusted identity. Verification is: fetch the card → confirm the source → check the signature → verify the signing key is bound to the agent identity → verify key validity → check capability claims → record the result → decide whether to admit the agent as verified. States: **VERIFIED**, **UNVERIFIED** (unsigned or unverifiable), **INVALID** (bad signature or identity mismatch). Unverified agents may be stored as pending-review records but must not automatically receive trusted-agent permissions. Agent Card JWS and push-notification JWS are different purposes and must not be mixed.

## 6. Messaging and Reliability

### 6.1 Dual-channel push authentication (top-priority blocker)

A2A native push authentication and platform-internal webhook authentication are **two independent channels** and must be strictly separated.

- **Channel A — A2A native push.** Per A2A v1.0.1 §4.3.1–4.3.3, authentication uses the `Authorization` request header (Bearer, Basic, and other supported HTTP authentication schemes). The receiver must use HTTPS, read `Authorization`, validate against the credentials in `TaskPushNotificationConfig`, check the Task ID, tenant ownership, and push configuration, and apply duplicate-notification idempotency. A2A native push must **not** be required to carry JWS, and must not be rejected for lacking platform extension fields.
- **Channel B — platform-internal webhook.** Uses JWS independently: signature algorithm, `kid`, signature timestamp, integrity-protected unique event ID, request-body integrity verification, key rotation, key revocation, anti-replay, and receiver-side dedup. Processing is: HTTPS → verify JWS algorithm → fetch public key by `kid` → verify signature → verify timestamp → verify event ID → check duplicates → verify task and tenant permissions → persist the event → acknowledge and process asynchronously. Anti-replay design follows RFC 7515 §10.10; the unique event ID must be part of the integrity-protected content.

Platform-internal JWS requirements must never be imposed on A2A native clients.

### 6.2 Unified message envelope

Every platform message carries: `message_id`, `event_id`, `task_id`, `context_id`, `tenant_id`, `sender_agent_id`, `recipient_agent_id`, `delegation_chain_id`, `protocol`, `protocol_version`, `connector_version`, `event_type`, `created_at`, `correlation_id`, `idempotency_key`, `payload_reference`, `trace_id`, `signature_algorithm`, `signature_kid`, `signature`, `signature_timestamp`.

Idempotency key format (platform-internal): `tenant_id:sender_agent_id:task_id:event_type:message_id`. Rules: normalize fields, reuse the original key on retry, generate a new key for a new business event, atomic check-and-register on the receiver, and never let a duplicate event produce a duplicate business side effect. A2A native push dedups by Task ID + status/event type. Platform extension fields must not be disguised as A2A-native fields. Dedup records are kept 7 days by default (at least 7 days for native push), extended when a task lives longer, and persisted — never memory-only.

### 6.3 Reliability

At-least-once delivery plus receiver-side idempotency. No end-to-end exactly-once promise. On timeout: do not immediately mark the task failed; query the original task status, keep a pending-confirmation state, retry only after confirming it is safe, escalate to human handling when it cannot be confirmed, and never silently discard a task. Communication Infrastructure owns message delivery; Orchestration owns task state and business decisions.

## 7. Tasks, Artifacts, and Lifecycle

### 7.1 Artifacts

Artifact states: `CREATED`, `APPENDING`, `COMPLETED`, `TRANSFER_FAILED`, `VALIDATION_FAILED`. Delivery must verify artifact ID, Task ID, content type, file size, content hash, storage location, version, and chunk information, and handle `append` and `lastChunk` correctly. An artifact is marked delivered only after the final chunk is confirmed and integrity verification passes. **Task success does not automatically mean the artifact was delivered.**

### 7.2 Agent lifecycle

States: `Pending`, `Active`, `Suspended`, `Revoked`, `Deleted`. On suspension: block new tasks and new delegations, revoke or restrict tokens, cancel tasks that can be safely cancelled, preserve unfinished task state, reclaim temporary credentials, restrict resource access, and write an audit record. Suspending an agent must never delete its historical tasks or audit records.

## 8. Security

### 8.1 Sandbox and tool boundaries

Agents run with: a tool whitelist, least privilege, network egress restrictions, filesystem isolation, CPU and memory limits, execution timeouts, subprocess control, credential isolation, and human approval for high-risk operations. An agent must never by default access the host's full files, network, and environment variables. Connector updates must be re-reviewed.

### 8.2 Internal threat model

Covered threats: malicious or compromised agent, stolen administrator identity, privilege-escalation in delegation, agent impersonation, cross-tenant data leakage, credential abuse, audit-log abuse, malicious connector update, artifact forgery, budget bypass, message-queue poisoning. Each threat must have: source → attack path → impact scope → protection → test case → acceptance evidence.

### 8.3 Audit log

Covers at minimum: login, authentication, permission changes, agent registration and suspension, task creation and delegation, artifact access, credential reads, webhook verification, budget pauses, administrator operations, and security anomalies. Records are append-only with hash-chain integrity verification. A hash chain alone does not prove absolute tamper-proofness; it must be combined with independent storage, access isolation, and integrity checks.

### 8.4 JWS and key management

Use reviewed JWS implementations. Forbid insecure algorithms and algorithm confusion. Verify signatures and claims. Support key rotation and revocation. State key purpose explicitly. Private keys must never enter ordinary databases or logs. Production keys are protected by a controlled key-management facility. Keys must not be shared arbitrarily across tenants.

### 8.5 Cost control

Metering dimensions: tenant, project, agent, task, provider, model, token, API call, external execution resources. Non-essential tasks (deferrable background analysis, delayable periodic work, non-critical index updates, non-essential recomputation, reschedulable low-priority work) may be paused; security, audit, data integrity, and critical task-state records must never be classified as non-essential. When a budget cap is reached: stop new non-essential tasks, block new over-budget assignments, preserve running task state, safely cancel cancellable tasks, allow necessary operations within safe bounds to complete, pause tasks whose safety is uncertain for human confirmation, and keep cost and audit records.

Cost authority: the vendor's official billing API is the authoritative source for actual cost; the vendor's official usage API is the basis for usage verification; platform token and API-call counts are internal estimates only and must never be presented as the final bill. Unsettled bills must be marked estimate or pending settlement. When cost data is unavailable, the platform must not default to unlimited pass-through.

## 9. Testing

### 9.1 Test cases

| ID | Case | Target count |
|---|---|---|
| T01 | Two-way message round trip | 100 |
| T02 | Duplicate delivery and idempotency | 100 |
| T03 | Task status tracking | 100 |
| T04 | Cross-agent delegation | 20 |
| T05 | Task cancellation | 20 |
| T06 | Disconnect recovery | 20 |
| T07 | Unauthorized access rejection | 20 |
| T08 | Cross-tenant isolation | 20 |
| T09 | Audit record correlation | All test tasks |
| T10 | Over-budget pause | Budget boundary |
| T11 | A2A native push authentication | Positive and negative |
| T12 | Platform JWS verification and anti-replay | Positive and negative |
| T13 | Agent Card verification | Positive and negative |
| T14 | Artifact integrity delivery | Positive and abnormal |
| T15 | Sandbox permission boundary | Positive and negative |

Every test records: test ID, agent name and version, protocol version, SDK version, connector version, test environment, input, expected result, actual result, evidence location, and PASS / FAIL / UNKNOWN.

### 9.2 Acceptance rules

- 100-run tests (T01–T03) check message loss, duplicate execution, status inconsistency, and sporadic errors. Sample counts are engineering acceptance criteria, not a claim of statistical reliability.
- Delivery success rate and result attribution rate (messages with complete Task ID, Message ID, and Trace ID linkage) are reported separately. Every one of the 100 runs must have a definite delivery outcome; silent loss is not allowed.
- 100 duplicate deliveries must produce no duplicate business side effects.
- Disconnect recovery: initial engineering target is **≤ 5 minutes** (from network/service recovery to message processing restored, task state re-synced, and normal send/receive resumed). Actual recovery time and failure cases are recorded for every test. This is not a production SLA.
- Unauthorized-access and cross-tenant-isolation tests must **all** refuse. A FAIL on a security-critical test cannot be passed by an aggregate pass rate.

### 9.3 Performance

Measured metrics: P50, P95, P99, maximum, failure rate, message-queue backlog, concurrent task count, recovery time. Measured separately for: message send-to-receive latency, agent task start latency, task status sync latency, webhook arrival latency, artifact delivery latency, fault recovery time. **No performance commitment may be stated without measurement.** Reference test environment: Ubuntu 24.04 LTS, 4 vCPU, 16 GB RAM, pinned Docker version, pinned PostgreSQL, pinned message queue, isolated test network, UTC time sync (converted to ET). Exact software versions, network conditions, and infrastructure are frozen before Stage 0 starts, and performance data from different environments must not be mixed. Baselines are captured first; formal performance thresholds are set after.

## 10. MVP Scope

The first version does not try to connect every vendor. It proves real interoperation between a small set of representative agents. MVP must have:

1. Agent registration and identity
2. Agent capability description and online status
3. Basic permission model
4. Connector management
5. A2A communication
6. API / Webhook connector example
7. MCP tool access
8. Real-time messaging and event sync
9. Task delegation and status return
10. Multi-agent parallel execution
11. Task relay and result handover
12. Basic failure handling and retry
13. Shared workspace
14. Execution records and audit log
15. Human approval for sensitive operations
16. Docker self-hosted deployment
17. Developer documentation and integration examples

MVP acceptance is measured by end-to-end collaboration success rate, repeatable tests, and security boundaries — not by connector count.

## 11. Roadmap

- **Stage 0 — Technical validation (in progress).** Prove the core with a runnable minimal prototype: two agents from different vendors, identity and discovery, two-way messaging, task delegation, status and result return, disconnect recovery, permission boundaries, and the A2A / MCP / API / Webhook combination. 18 deliverables (below). Current estimate ~30–40 person-days (pending independent review; no fixed cap, scope unchanged, rolling updates).
- **Stage 1 — MVP.** The 17 MVP capabilities above, Docker self-hosting, developer docs.
- **Stage 2 — v1.0.** Hardened release: wider vendor coverage, connector review process, production deployment guidance.

Stage 0 deliverables (18, all retained):
1. Runnable minimal technical prototype
2. A2A version verification report
3. MCP version verification report
4. Agent discovery verification
5. Two-way messaging test
6. Task status test
7. Authentication and authorization test
8. Message bus test
9. Disconnect recovery test
10. Security risk report
11. Cost model
12. Executable conformance test suite
13. Revised technical architecture
14. MVP Go/No-Go report
15. Artifact integrity delivery test report
16. Multi-tenant isolation and sandbox test report
17. Dual-channel push authentication and JWS anti-replay test report
18. Performance baseline and cost-control verification report

## 12. Governance

- **License:** Apache License 2.0 is proposed; the final license is confirmed by the project owner.
- **Repository contents:** LICENSE, README, CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, issue templates, PR templates, release specification, security vulnerability disclosure process, third-party connector review process. Third-party connectors are reviewed for source, dependencies, permissions, credentials, network access, protocol compatibility, and security boundaries.
- **Team:** a six-member team — one dispatcher, architecture and documentation, independent review, implementation and execution verification, protocol and compatibility verification, integration testing. Final approval authority rests with the project owner.
- **Task discipline:** every task carries an ID, goal, background, owner, deliverables, acceptance criteria, dependencies, deadline, and status (PASS / FAIL / UNKNOWN). No self-review substitutes for independent review; important technical conclusions are checked by another member; at most two rework rounds; a FAIL can never be marked complete; UNKNOWN must state the missing evidence; execution records are never fabricated.
- **No-go principles (inviolable):**
  1. Never present a model API as agent interoperation.
  2. Never write unverified protocol compatibility as implemented.
  3. Never let agents share raw account credentials.
  4. Never allow cross-tenant unauthorized access.
  5. Never let duplicate messages produce duplicate business side effects.
  6. Never silently lose a task.
  7. Never run without limit after a cost overrun.
  8. Never proceed after a security-critical test failure.
  9. Never add a project agent without confirmation.
  10. Never start Stage 0 without the project owner's approval.

## 13. Current Status

- **Plan version:** v0.2.6 (2026-11-14)
- **Stage 0:** approved and in progress (owner decision, 2026-11-14)
- **Next steps:** (1) build the runnable minimal prototype and freeze the §23 reference environment; (2) A2A and MCP verification reports; (3) integration test and T01–T15 case preparation; (4) independent duration-estimate review in parallel; (5) compile the Stage 0 acceptance report.
- **Open items:** conformance test standard freeze, development-environment verification, and security-critical blocker clearance are being completed in parallel with execution; a FAIL or UNKNOWN on any safety-critical item still blocks further progress.

---

*This whitepaper is derived from the project plan v0.2.6. Where the plan and this document differ, the plan governs. Estimates are planning figures pending independent review and must not be read as delivery commitments.*
