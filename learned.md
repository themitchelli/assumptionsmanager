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
