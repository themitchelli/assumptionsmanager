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

## 2026-01-19 12:30 - PRD-008: Tenant and User Management - COMPLETE

All five user stories completed:
- US-001: GET /tenants (super_admin only) - list all tenants
- US-002: POST /tenants (super_admin only) - create new tenant
- US-003: GET /users - list users in current tenant (filtered by JWT tenant_id)
- US-004: PATCH /users/{id} - update user role (admin only, cannot demote self)
- US-005: DELETE /users/{id} - remove user (admin only, cannot delete self)

Role hierarchy implemented: super_admin (platform), admin (tenant), analyst, viewer
Tenant isolation via WHERE clause (note: RLS bypassed due to superuser DB connection)
Files changed: backend/main.py, backend/routers/users.py, backend/schemas.py
Tests: manual API testing passed all acceptance criteria

## 2026-01-19 13:05 - PRD-009 US-001: Create assumption table - COMPLETE

- POST /tables endpoint implemented with full column definitions support
- Database schema updated: added assumption_columns, assumption_rows, assumption_cells tables
- Removed unused assumption_versions and assumption_data tables (JSONB approach replaced with normalized model)
- Added effective_date column to assumption_tables
- Validates column data_types (text, integer, decimal, date, boolean)
- Validates effective_date format (YYYY-MM-DD)
- Requires analyst or admin role (viewer gets 403)
- tenant_id set automatically from JWT
- Files changed: backend/init.sql, backend/schemas.py, backend/routers/tables.py, backend/main.py
- Tests: manual API testing passed all acceptance criteria

## 2026-01-19 13:12 - PRD-009 US-002: List assumption tables - COMPLETE

- GET /tables endpoint returns list of tables in current tenant
- Tenant isolation enforced via WHERE clause filtering by tenant_id from JWT
- Returns metadata only: id, name, description, effective_date, created_by, created_at
- All authenticated roles can access (viewer, analyst, admin tested)
- Files changed: backend/routers/tables.py
- Tests: manual API testing passed all acceptance criteria

## 2026-01-19 13:20 - PRD-009 US-003: Get assumption table with data - COMPLETE

- GET /tables/{id} endpoint returns full table data including rows and cells
- Includes metadata, column definitions, all rows with cell values
- Cell values cast to appropriate Python types based on column data_type (integer, decimal, text, date, boolean)
- Returns 404 if table not found or not in user's tenant (tenant isolation enforced)
- All authenticated roles can access (viewer, analyst, admin)
- Files changed: backend/schemas.py (RowResponse, TableDetailResponse), backend/routers/tables.py
- Tests: manual API testing passed all acceptance criteria

## 2026-01-19 13:28 - PRD-009 US-004: Update table metadata - COMPLETE

- PATCH /tables/{id} endpoint updates metadata fields (name, description, effective_date)
- Partial updates supported (only provided fields are updated)
- Does not modify columns or row data
- Requires analyst or admin role (viewer gets 403)
- Returns 404 if table not found or not in user's tenant
- Files changed: backend/schemas.py (TableUpdate), backend/routers/tables.py
- Tests: manual API testing passed all acceptance criteria

## 2026-01-20 00:05 - PRD-009 US-005: Delete assumption table - COMPLETE

- DELETE /tables/{id} endpoint implemented
- Returns 204 No Content on successful deletion
- Requires analyst or admin role (viewer gets 403)
- Returns 404 if table not found or not in user's tenant (tenant isolation enforced)
- Cascade deletes all related columns, rows, and cells via FK constraints
- Files changed: backend/routers/tables.py
- Tests: manual API testing passed all acceptance criteria

## 2026-01-20 00:15 - PRD-009 US-005: Add rows to table - COMPLETE

- POST /tables/{id}/rows endpoint implemented
- Accepts array of rows with column_name: value pairs
- Validates cell values against column data_types (integer, decimal, text, date, boolean)
- Row indices auto-assigned (append to end)
- Returns created rows with ids and cell data
- Requires analyst or admin role (viewer gets 403)
- Files changed: backend/schemas.py (RowCreate, RowsCreate), backend/routers/tables.py
- Tests: manual API testing passed all acceptance criteria

## 2026-01-20 00:20 - PRD-009 US-006: Update row data - COMPLETE

- PATCH /tables/{table_id}/rows/{row_id} endpoint implemented
- Accepts partial updates (only specified columns updated)
- Validates values against column data_types
- Uses UPSERT to handle cells that may not exist yet
- Returns updated row with all cell values
- Requires analyst or admin role
- Files changed: backend/routers/tables.py
- Tests: manual API testing passed all acceptance criteria

## 2026-01-20 00:25 - PRD-009 US-007: Delete rows - COMPLETE

- DELETE /tables/{table_id}/rows/{row_id} endpoint implemented
- Returns 204 No Content on successful deletion
- Requires analyst or admin role
- Cascades to delete all cells in the row via FK constraint
- Returns 404 if row not found or table not in tenant
- Files changed: backend/routers/tables.py
- Tests: manual API testing passed all acceptance criteria

## 2026-01-20 00:30 - PRD-009 US-008: Delete assumption table - COMPLETE

- DELETE /tables/{id} endpoint updated to require admin role only
- Previously allowed analyst role; now only admin can delete tables
- Returns 204 on success, 404 if not found
- Cascades: columns, rows, cells all deleted via FK constraints
- Files changed: backend/routers/tables.py
- Tests: manual API testing passed all acceptance criteria

## 2026-01-20 00:30 - PRD-009: Assumption Tables CRUD - COMPLETE

All eight user stories completed:
- US-001: POST /tables - create table with columns
- US-002: GET /tables - list tables in tenant
- US-003: GET /tables/{id} - get table with full data
- US-004: PATCH /tables/{id} - update table metadata
- US-005: POST /tables/{id}/rows - add rows to table
- US-006: PATCH /tables/{table_id}/rows/{row_id} - update row data
- US-007: DELETE /tables/{table_id}/rows/{row_id} - delete rows
- US-008: DELETE /tables/{id} - delete table (admin only)

Full CRUD operations for assumption tables and rows working with tenant isolation.

## 2026-01-20 07:30 - PRD-010: Assumption Table Versioning - COMPLETE

All six user stories completed:
- US-001: POST /tables/{id}/versions - create version snapshot
- US-002: GET /tables/{id}/versions - list version history
- US-003: GET /tables/{id}/versions/{version_id} - get version with full data
- US-004: POST /tables/{id}/versions/{version_id}/restore - restore from version
- US-005: DELETE /tables/{id}/versions/{version_id} - delete version (admin only)
- US-006: GET /tables/{id}/versions/compare?v1=&v2= - diff two versions

Database schema: assumption_versions and assumption_version_cells tables added.
Versioning logic isolated in backend/services/versioning/ for future extraction.
Diff algorithm is entity-agnostic with row-by-row comparison.

Files changed:
- backend/init.sql (new tables)
- backend/services/versioning/service.py (VersioningService)
- backend/routers/versions.py (all endpoints)
- backend/schemas.py (version schemas)
- backend/main.py (router registration)

Tests: manual API testing passed all acceptance criteria

