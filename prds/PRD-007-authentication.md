# PRD-007: Authentication

**Status:** Ready
**Phase:** 1 (MVP)
**Depends On:** PRD-006

---

## Objective

Implement JWT-based authentication with bcrypt password hashing. Users belong to tenants, and authentication sets the tenant context for RLS.

---

## User Stories

### Story 1: User Registration
**As** a tenant admin
**I want** to register new users
**So that** team members can access the system

**Acceptance Criteria:**
- POST `/auth/register` accepts email, password, tenant_id
- Password is hashed with bcrypt before storage
- Returns user object (without password)
- Rejects duplicate email within same tenant

### Story 2: User Login
**As** a user
**I want** to login with email and password
**So that** I can access my tenant's data

**Acceptance Criteria:**
- POST `/auth/login` accepts email, password
- Validates password against bcrypt hash
- Returns JWT token (24h expiry)
- JWT payload includes: user_id, tenant_id, role

### Story 3: Protected Routes
**As** the system
**I want** to verify JWT on protected routes
**So that** only authenticated users access data

**Acceptance Criteria:**
- Middleware extracts JWT from Authorization header
- Invalid/expired tokens return 401
- Valid tokens set tenant context for RLS
- `/tenants` endpoint requires authentication

### Story 4: Current User Endpoint
**As** a user
**I want** to get my profile info
**So that** the frontend knows who I am

**Acceptance Criteria:**
- GET `/auth/me` returns current user
- Requires valid JWT
- Returns user object without password

---

## Technical Notes

- Use `python-jose` for JWT
- Use `passlib[bcrypt]` for password hashing
- Set `app.current_tenant` in database session for RLS
- Token expiry: 24 hours

---

## Definition of Done

- [ ] All four stories implemented
- [ ] Tests pass
- [ ] Can register user, login, access protected route
- [ ] RLS filters data by tenant from JWT