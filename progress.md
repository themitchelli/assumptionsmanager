# Progress Log

Session history for this project. Append-only.

<!--
Entry format (append new entries below the line):

## YYYY-MM-DD HH:MM - US-XXX: Story Title - COMPLETE

- Summary of what was implemented
- Files changed: list key files
- Tests: passed/added

For blocked stories, use:

## YYYY-MM-DD HH:MM - US-XXX: Story Title - BLOCKED

- What was attempted
- What's blocking progress
- Suggested resolution
-->

---
## 2026-01-18 15:00 - Phase 0: Infrastructure - COMPLETE

- Pi 5 8GB hardware configured and running headless
- Docker + Docker Compose installed and working
- Caddy reverse proxy with auto-SSL configured
- GitHub Actions CI/CD with self-hosted runner on Pi
- Hello World FastAPI deployed and validated
- Live at https://assumptionsmanager.ddns.net
- Files: backend/main.py, docker-compose.yml, .github/workflows/deploy.yml

## 2026-01-18 16:00 - PRD-006: Database Setup - COMPLETE

- PostgreSQL 16 container running
- Connected to backend service
- Ready for schema and RLS policies

## 2026-01-19 10:10 - US-001: User Registration - COMPLETE

- POST /auth/register endpoint implemented and tested
- Password hashing with bcrypt via passlib
- Returns user object without password (UserResponse schema)
- Duplicate email within tenant returns 409 Conflict
- Files changed: backend/routers/auth.py, backend/requirements.txt
- Tests: manual API testing passed all acceptance criteria

## 2026-01-19 10:18 - US-002: User Login - COMPLETE

- POST /auth/login endpoint implemented and tested
- Validates password against bcrypt hash (wrong password returns 401)
- Returns JWT token with 24h expiry
- JWT payload contains user_id, tenant_id, role
- Files changed: backend/routers/auth.py
- Tests: manual API testing passed all acceptance criteria

## 2026-01-19 10:28 - US-003: Protected Routes - COMPLETE

- JWT authentication dependency (get_current_user) implemented
- TokenData dataclass for typed token payload
- Invalid/expired tokens return 401 Unauthorized
- /tenants endpoint now requires authentication
- RLS tenant context set via app.current_tenant
- Files changed: backend/auth.py, backend/database.py, backend/main.py
- Tests: manual API testing passed all acceptance criteria

## 2026-01-19 10:35 - US-004: Current User Endpoint - COMPLETE

- GET /auth/me endpoint implemented and tested
- Requires valid JWT authentication
- Returns user object without password (UserResponse schema)
- Files changed: backend/routers/auth.py
- Tests: manual API testing passed all acceptance criteria

## 2026-01-19 10:35 - PRD-007: Authentication - COMPLETE

All four user stories completed:
- US-001: User Registration
- US-002: User Login
- US-003: Protected Routes
- US-004: Current User Endpoint

Full auth flow working: register → login → access protected routes → get profile

## 2026-01-19 11:00 - ENH-007 US-001: Mark PRD complete in FADE.md - COMPLETE

- Updated prompt.md Session Exit Protocol with new step 4
- Step 4 instructs: when all stories pass, mark PRD checkbox complete in FADE.md
- Handles missing PRD gracefully (skip silently)
- Updated "What NOT to do" section to clarify FADE.md exception for checkboxes
- Files changed: prompt.md
- Tests: manual review of acceptance criteria

