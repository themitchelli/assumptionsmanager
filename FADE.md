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

### Phase 0: Infrastructure (CURRENT)
- [x] PRD-001: Pi Hardware Setup
- [x] PRD-002: Docker + Base Config  
- [x] PRD-003: Caddy Reverse Proxy + SSL
- [ ] PRD-004: GitHub Actions CI/CD
- [ ] PRD-005: Hello World Validation

### Phase 1: MVP (4 weeks)
- [ ] Upload CSV assumption tables
- [ ] Version control with history
- [ ] Visual diff between versions
- [ ] Basic approval workflow
- [ ] Export to CSV
- [ ] Audit trail

---

## Deployment

**Local:** docker compose up --build

**Production:** Push to main -> GitHub Actions -> Auto-deploy to Pi

**Pi Access:** ssh themitchelli@fade-pi

---

## Session Boundaries

**Allowed:** Modify backend/, frontend/, docs/, docker-compose.yml

**Needs Approval:** CI/CD changes, database migrations, auth changes

**Never:** Push to main directly, commit secrets