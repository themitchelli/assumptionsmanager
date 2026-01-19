# Assumptions Manager

<!-- FADE.md - Project context for AI coding agents. This file is READ-ONLY for agents. -->

---

## Project Overview

Actuarial Assumptions Manager - a standalone SaaS product that solves assumption governance pain for actuarial teams.

**What it does:**
- Upload assumption tables (mortality, lapse, expense rates as CSV/Excel)
- Git-style version control with full history
- Visual diff between versions (heatmaps showing what changed)
- Approval workflow (maker/checker pattern)
- Export to CSV/Excel (feeds into Prophet, MG-ALFA, or any legacy platform)
- Complete audit trail
- Bitemporal queries (effective date vs system date)

**Why it matters:**
- Actuaries spend 50%+ of pre-model time on assumption management
- Regulators (Solvency II, IFRS 17) demand auditable assumption lineage
- Prophet/MG-ALFA are calculation engines, not governance tools

**Tech Stack:**
- Frontend: SvelteKit + Tailwind
- Backend: Python FastAPI
- Database: PostgreSQL 16 (Row-Level Security for multi-tenant)
- Auth: JWT + bcrypt
- Reverse Proxy: Caddy (auto-SSL)
- Container: Docker + docker-compose
- CI/CD: GitHub Actions (self-hosted runner on Pi)
- Target: Raspberry Pi 5 (8GB)

---

## Architecture

### Network Topology

Internet -> assumptionsmanager.ddns.net:443 -> Router (No-IP) -> fade-pi:443 -> Caddy -> Containers

### Multi-Tenant Model

- Row-Level Security (RLS) in PostgreSQL
- Every table has tenant_id
- Zero chance of cross-tenant data leak

---

## Coding Standards

- **Python:** Black formatter, type hints everywhere
- **TypeScript:** Strict mode, no any
- **SQL:** Explicit column lists, no SELECT *
- **Commits:** Conventional commits (feat:, fix:, docs:, chore:)
- **Branches:** Feature branches, squash merge to main

---

## Development Phases

### Phase 0: Infrastructure ✅ COMPLETE
- [x] PRD-001: Pi Hardware Setup
- [x] PRD-002: Docker + Base Config  
- [x] PRD-003: Caddy Reverse Proxy + SSL
- [x] PRD-004: GitHub Actions CI/CD
- [x] PRD-005: Hello World Validation
- [x] PRD-006: Database Setup (PostgreSQL running)

### Phase 1: MVP ← CURRENT
- [x] PRD-007: Authentication (JWT + bcrypt) ✅
- [ ] PRD-008: Tenant & User Management
- [ ] PRD-009: Assumption Tables CRUD
- [ ] PRD-010: Version Control
- [ ] PRD-011: Visual Diff
- [ ] PRD-012: Approval Workflow
- [ ] PRD-013: Export to CSV

---

## Development Environment

### Prerequisites

- Docker Desktop installed on development machine
- Verify: `docker --version` and `docker compose version`

### Local Development

```bash
# Start local stack with hot reload
docker compose up --build

# API available at: http://localhost:8000
# PostgreSQL at: localhost:5432

# Test the health endpoint
curl http://localhost:8000/health
```

**Hot Reload:** Changes to `backend/` files automatically reload without rebuild.

**Local Database:** PostgreSQL runs on port 5432 with credentials:
- User: `assumptions`
- Password: `assumptions`
- Database: `assumptions`

### Production Deployment

```bash
# Push to main triggers auto-deploy to Pi
git push origin main
```

GitHub Actions uses `docker-compose.prod.yml` which:
- Connects to Caddy via external 'web' network
- No exposed ports (Caddy handles routing)
- No volume mounts (uses built image)

### Workflow

1. **Develop locally:** `docker compose up --build`
2. **Test at:** `http://localhost:8000`
3. **Run tests:** (before pushing)
4. **Deploy:** `git push origin main`
5. **Verify:** `https://assumptionsmanager.ddns.net/health`

---

## Deployment Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Local development with hot reload |
| `docker-compose.prod.yml` | Production on Pi (used by GitHub Actions) |

**Pi Access:** ssh themitchelli@fade-pi

---

## Session Boundaries

**Allowed:** Modify backend/, frontend/, docs/, docker-compose.yml

**Needs Approval:** CI/CD changes, database migrations, auth changes

**Never:** Push to main directly, commit secrets