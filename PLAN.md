# Harbor — Development Plan

## Vision

Harbor is an Agent Platform Management system (APIM for AI Agents) built on AWS,
providing registry, discovery, lifecycle management, and governance for AI agents
running on AWS Bedrock AgentCore Runtime.

---

## Phase 0: Project Foundation

### 0.1 Development Environment
- [ ] Initialize Python venv, install dependencies via uv
- [ ] Configure ruff, mypy, pytest
- [ ] Verify project builds and imports work

### 0.2 Install ui-ux-pro-max Skill
- [ ] Install ui-ux-pro-max skill to `~/.kiro/skills/`
- [ ] Verify skill is available in Kiro CLI

---

## Phase 1: CDK Infrastructure

### 1.1 CDK Project Setup
- [ ] Initialize CDK app (TypeScript) under `infrastructure/cdk/`
- [ ] Define CDK stack structure

### 1.2 Data Layer
- [ ] DynamoDB table `harbor-agent-registry`
  - PK/SK composite key
  - GSI: `status-index` (PK=status, SK=updated_at)
  - PAY_PER_REQUEST billing
  - Point-in-time recovery enabled

### 1.3 Backend Compute
- [ ] Lambda function for Harbor API
  - Python 3.12 runtime
  - Mangum adapter (FastAPI → Lambda)
  - IAM role with DynamoDB read/write
  - Environment variables (table name, region)
- [ ] API Gateway (HTTP API)
  - Routes: /api/* → Lambda integration
  - CORS configuration
  - (Optional) Cognito authorizer

### 1.4 Frontend Hosting
- [ ] S3 bucket for static frontend assets
- [ ] CloudFront distribution
  - S3 origin for static files
  - API Gateway origin for /api/*
  - WAF WebACL (rate limiting, common rules)
- [ ] OAC (Origin Access Control) for S3

### 1.5 Auth (Optional Phase 1)
- [ ] Cognito User Pool for admin access
- [ ] Cognito integration with API Gateway

### 1.6 CDK Deploy Script
- [ ] `scripts/deploy.sh` — one-command deployment
- [ ] `scripts/destroy.sh` — cleanup

---

## Phase 2: Backend API (Complete)

### 2.1 Core Models (Refine)
- [ ] Review and finalize AgentRecord schema
- [ ] Add AgentVersion model (version history)
- [ ] Add AuditEntry model (who changed what when)
- [ ] Add HealthStatus model (heartbeat, last_seen, error_count)

### 2.2 DynamoDB Store (Enhance)
- [ ] Add version snapshot writes (VER#{version} SK)
- [ ] Add audit log writes (AUDIT#{timestamp} SK)
- [ ] Add health status writes (HEALTH SK)
- [ ] Add batch operations (batch_get for discovery)
- [ ] Add pagination support (LastEvaluatedKey)

### 2.3 Registry Service (Enhance)
- [ ] Version management — register new version, rollback, list versions
- [ ] Deprecation workflow — deprecate with sunset date, notify dependents
- [ ] Bulk import — register multiple agents from JSON/YAML
- [ ] Validation — schema validation on register/update

### 2.4 Discovery Service (Enhance)
- [ ] Weighted routing — priority + random weight for load distribution
- [ ] Dependency resolution — find all agents an agent depends on
- [ ] Skill-based search — fuzzy match on skill descriptions
- [ ] Health-aware discovery — exclude unhealthy agents

### 2.5 Health & Monitoring
- [ ] Health check endpoint — agents report heartbeat via PUT /agents/{id}/health
- [ ] Health status tracking — last_seen, consecutive_failures, status
- [ ] Stale agent detection — mark agents unhealthy after N missed heartbeats
- [ ] Health summary endpoint — GET /health/summary (total, healthy, unhealthy counts)

### 2.6 A2A Agent Card Sync
- [ ] Import endpoint — POST /agents/import-a2a with URL
- [ ] Fetch /.well-known/agent-card.json from agent URL
- [ ] Map A2A Agent Card fields to AgentRecord
- [ ] Periodic sync — scheduled re-fetch of registered agent cards

### 2.7 Audit Log
- [ ] Record all mutations (register, update, delete, status change)
- [ ] GET /agents/{id}/audit — list audit entries
- [ ] GET /audit — global audit log with filters

### 2.8 Notifications (EventBridge)
- [ ] Emit events on agent status change
- [ ] Emit events on agent registration/deregistration
- [ ] EventBridge rule → SNS topic for alerts

### 2.9 Security & Access Control
- [ ] API key or Cognito JWT validation on write endpoints
- [ ] Read endpoints optionally public or authenticated
- [ ] Rate limiting via API Gateway throttling

### 2.10 Lambda Packaging
- [ ] Mangum adapter integration
- [ ] Lambda handler entry point
- [ ] Docker-based Lambda build (for dependencies)

---

## Phase 3: Frontend (React + Tailwind)

### 3.1 Project Setup
- [ ] Initialize React app under `frontend/`
- [ ] Install Tailwind CSS, React Router, Axios/fetch
- [ ] Configure build for S3 deployment

### 3.2 Design System (via ui-ux-pro-max)
- [ ] Use ui-ux-pro-max to generate design system
  - Color palette (aligned with Harbor/nautical theme)
  - Typography (font pairings)
  - Component style guide
  - Layout patterns
- [ ] Create shared UI components (Button, Card, Table, Badge, Modal, Form)

### 3.3 Pages — Dashboard
- [ ] Agent count summary cards (total, active, inactive, deprecated, maintenance)
- [ ] Health status overview (healthy / unhealthy / unknown)
- [ ] Recent activity feed (last N audit entries)
- [ ] Quick actions (register agent, run discovery)

### 3.4 Pages — Agent Catalog
- [ ] Agent list with search, filter by status/capability/phase
- [ ] Card or table view toggle
- [ ] Sort by name, status, updated_at, priority
- [ ] Pagination

### 3.5 Pages — Agent Detail
- [ ] Agent metadata display (all fields)
- [ ] Inline edit for user-configurable fields (model_id, timeout, priority, tags)
- [ ] Skills list with expandable details
- [ ] Routing rules editor
- [ ] Version history tab
- [ ] Audit log tab
- [ ] Health status tab
- [ ] Actions: activate, deactivate, deprecate, delete

### 3.6 Pages — Register Agent
- [ ] Form for creating new agent
- [ ] JSON import option (paste A2A Agent Card JSON)
- [ ] URL import option (fetch from /.well-known/agent-card.json)
- [ ] Validation and preview before submit

### 3.7 Pages — Discovery
- [ ] Search by capability input
- [ ] Search by phase input
- [ ] Results list with priority ranking
- [ ] "Resolve best agent" one-click action

### 3.8 Pages — Dependency Graph
- [ ] Visual graph of agent dependencies (D3.js or similar)
- [ ] Click node to navigate to agent detail
- [ ] Filter by phase or capability group

### 3.9 Pages — Audit Log
- [ ] Global audit log table
- [ ] Filter by agent, action type, date range
- [ ] Expandable row for change details

### 3.10 Pages — Settings
- [ ] Platform configuration (default timeout, retry policy)
- [ ] Notification preferences
- [ ] User management (if Cognito enabled)

### 3.11 Frontend Build & Deploy
- [ ] Build script (npm run build)
- [ ] S3 sync script
- [ ] CloudFront invalidation

---

## Phase 4: Integration & Testing

### 4.1 Backend Unit Tests
- [ ] Models — serialization, validation
- [ ] Store — CRUD, discovery queries (moto mock)
- [ ] Registry service — lifecycle operations
- [ ] Discovery service — routing, resolution
- [ ] API routes — endpoint tests (httpx + TestClient)

### 4.2 Infrastructure Tests
- [ ] CDK snapshot tests
- [ ] CDK assertion tests (resource properties)

### 4.3 Integration Tests
- [ ] Deploy to AWS, run API tests against real endpoints
- [ ] Register sample agents, verify discovery
- [ ] A2A import test

### 4.4 Frontend Tests
- [ ] Component tests (React Testing Library)
- [ ] E2E smoke test (Playwright or Cypress)

---

## Phase 5: Noah Integration

### 5.1 Noah Orchestrator Integration
- [ ] Replace hardcoded _AGENT_LIST with Harbor API call
- [ ] Replace orchestrator_dispatch.py hardcoded routing with Harbor discovery
- [ ] Add @noah_agent decorator that auto-registers to Harbor on startup

### 5.2 Noah Agent Migration
- [ ] Register all 9 existing Noah agents in Harbor
- [ ] Add AgentDescriptor metadata to each agent class
- [ ] Verify orchestrator can discover and dispatch via Harbor

### 5.3 Bidirectional Sync
- [ ] Noah agents report health to Harbor
- [ ] Harbor status changes reflected in Noah orchestrator behavior

---

## Phase 6: Advanced Features (Future)

- [ ] Agent A/B testing — route percentage of traffic to different versions
- [ ] Cost tracking — per-agent LLM token usage aggregation
- [ ] SLA monitoring — response time tracking, alerting on degradation
- [ ] Agent marketplace — share agent definitions across teams
- [ ] Terraform/CDK codegen — generate IaC from agent registry
- [ ] CLI tool — `harbor register`, `harbor discover`, `harbor status`

---

## Architecture Summary

```
User → WAF → CloudFront ─→ S3 (React SPA)
                          ─→ API Gateway (/api/*) → Lambda (FastAPI + Mangum)
                                                        ↓
                                                   DynamoDB
                                                   (harbor-agent-registry)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Tailwind CSS |
| Design | ui-ux-pro-max skill |
| API | FastAPI + Mangum (Lambda adapter) |
| Compute | AWS Lambda (Python 3.12) |
| Gateway | API Gateway HTTP API |
| Storage | DynamoDB (single-table) |
| CDN | CloudFront + S3 |
| Security | WAF + (optional) Cognito |
| IaC | AWS CDK (TypeScript) |
| CI/CD | GitHub Actions (future) |
