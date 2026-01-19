# Learned

Discoveries and insights from development sessions. Append-only.

<!--
Entry format (append new entries below the line):

## YYYY-MM-DD - Discovery Title

**Context:** What were you doing when you discovered this?
**Learning:** What did you learn?
**Relevance:** Why does this matter for future work?
**Files affected:** Which modules/files does this apply to?

Only add learnings that are:
- Reusable (not story-specific details)
- Non-obvious (things a future session wouldn't know)
- Actionable (helps avoid mistakes or speeds up work)
-->

---

## 2026-01-19 - Passlib bcrypt dependency split

**Context:** Debugging 500 errors on the /auth/register endpoint.
**Learning:** Using `passlib[bcrypt]` as a single package in requirements.txt can cause issues in some environments. Split into separate `passlib==1.7.4` and `bcrypt==4.1.2` packages for reliability.
**Relevance:** Future auth-related work should maintain this package split pattern.
**Files affected:** backend/requirements.txt

## 2026-01-19 - Expose error details in 500 responses during development

**Context:** Registration endpoint returned generic "Internal Server Error" with no details.
**Learning:** Wrap endpoint logic in try/except and return the actual exception message in the 500 detail field. This helps debug issues in deployed environments where you can't easily access container logs.
**Relevance:** Apply this pattern to other endpoints that might have complex database operations.
**Files affected:** backend/routers/auth.py

## 2026-01-19 - PostgreSQL superuser bypasses RLS even with FORCE enabled

**Context:** Implementing tenant isolation for GET /users endpoint. RLS policies were configured with FORCE ROW LEVEL SECURITY, but queries still returned all rows.
**Learning:** PostgreSQL superusers ALWAYS bypass RLS, even when `ALTER TABLE ... FORCE ROW LEVEL SECURITY` is enabled. The `assumptions` database user is a superuser, which means RLS policies have no effect. To properly enforce RLS, the application must connect using a non-superuser role. Current workaround: use WHERE clauses to filter by tenant_id from JWT instead of relying on RLS.
**Relevance:** Future work requiring strict RLS enforcement needs either: (1) create a non-superuser application role, or (2) continue using WHERE clause filtering. For now, WHERE clause approach works but adds boilerplate to each query.
**Files affected:** backend/routers/users.py, any future endpoints needing tenant isolation

## 2026-01-19 - Child tables without RLS need JOIN-based tenant isolation

**Context:** Designing the assumption tables data model with parent (assumption_tables) and child tables (assumption_columns, assumption_rows, assumption_cells).
**Learning:** Child tables that don't have tenant_id columns should NEVER be queried directly. Always access them via JOINs through the parent table (assumption_tables) which has RLS/tenant_id. This ensures tenant isolation is enforced at the parent level. For writes, first verify the parent table belongs to the user's tenant, then insert into child tables using that verified table_id.
**Relevance:** All future CRUD operations on assumption_columns, assumption_rows, and assumption_cells must go through assumption_tables first. Never query child tables directly without a tenant-verified table_id filter.
**Files affected:** backend/routers/tables.py, any future endpoints touching assumption data
