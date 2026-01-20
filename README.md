# Assumptions Manager

**Git-style version control for actuarial assumptions.**

A SaaS platform enabling actuaries to manage mortality, lapse, and expense tables with approval workflows, audit trails, and versioning – the governance that spreadsheets can't provide.

🔗 **Live Demo:** https://assumptionsmanager.ddns.net  
📚 **API Docs:** https://assumptionsmanager.ddns.net/docs

---

## 🤖 Built 100% by AI Agents

This entire product was developed as a **thought experiment in agentic software development** by [Steve Mitchell](https://www.linkedin.com/in/stevemitchelli/), Director of Product Engineering at Milliman.

Every line of code, database migration, Docker configuration, and CI/CD pipeline was written by Claude (Anthropic's AI) using the FADE (Framework for Agentic Development and Engineering) methodology. A human directed the work through PRDs and reviewed outputs, but never wrote code directly.

**The question:** Can an AI agent build production-quality software autonomously, overnight, while the human sleeps?

**The answer:** Yes. You're looking at it.

---

## MVP Features (Phase 1)

| Feature | Description | Status |
|---------|-------------|--------|
| **Multi-tenant Architecture** | PostgreSQL Row-Level Security isolates tenant data | ✅ Complete |
| **Authentication** | JWT-based auth with role-based access control | ✅ Complete |
| **User Management** | Admin/analyst/viewer roles per tenant | ✅ Complete |
| **Assumption Tables CRUD** | Create, read, update, delete actuarial tables | ✅ Complete |
| **Flexible Schema** | Tables define their own columns (text, decimal, date, boolean) | ✅ Complete |
| **Version Control** | Git-style snapshots with immutable version history | ✅ Complete |
| **Visual Diff** | Compare two versions to see what changed | ✅ Complete |
| **Approval Workflow** | Submit → Review → Approve/Reject with audit trail | ✅ Complete |
| **CSV Export** | Export tables for use in actuarial models | ✅ Complete |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11 + FastAPI |
| Database | PostgreSQL 16 with Row-Level Security |
| Auth | JWT tokens with bcrypt password hashing |
| Deployment | Docker + GitHub Actions CI/CD |
| Infrastructure | Raspberry Pi 5 (yes, really – £80 production server) |
| Reverse Proxy | Caddy with automatic HTTPS |
| Frontend | API-first (SvelteKit planned for Phase 2) |

---

## Quick Start (Local Development)

```bash
# Clone the repository
git clone https://github.com/themitchelli/assumptionsmanager.git
cd assumptionsmanager

# Start with Docker Compose
docker compose up --build

# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

---

## API Overview

### Authentication
```bash
# Register a new user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "analyst@example.com", "password": "securepassword", "tenant_id": "..."}'

# Login and get JWT token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "analyst@example.com", "password": "securepassword"}'
```

### Assumption Tables
```bash
# Create a mortality table
curl -X POST http://localhost:8000/tables \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mortality Rates Q3 2025",
    "description": "Updated mortality assumptions for Q3 valuation",
    "columns": [
      {"name": "age", "data_type": "integer"},
      {"name": "gender", "data_type": "text"},
      {"name": "qx", "data_type": "decimal"}
    ]
  }'

# List all tables
curl http://localhost:8000/tables \
  -H "Authorization: Bearer <token>"

# Export to CSV
curl http://localhost:8000/tables/{id}/export/csv \
  -H "Authorization: Bearer <token>" \
  -o mortality_rates.csv
```

### Version Control
```bash
# Create a version snapshot
curl -X POST http://localhost:8000/tables/{id}/versions \
  -H "Authorization: Bearer <token>" \
  -d '{"comment": "Pre-Q3 review snapshot"}'

# Compare two versions
curl http://localhost:8000/tables/{id}/versions/compare?v1={version1}&v2={version2} \
  -H "Authorization: Bearer <token>"
```

### Approval Workflow
```bash
# Submit for approval
curl -X POST http://localhost:8000/tables/{id}/versions/{version_id}/submit \
  -H "Authorization: Bearer <token>"

# Approve (admin only)
curl -X POST http://localhost:8000/tables/{id}/versions/{version_id}/approve \
  -H "Authorization: Bearer <token>" \
  -d '{"comment": "Reviewed and approved for production use"}'
```

---

## Role-Based Access

| Role | Capabilities |
|------|-------------|
| **viewer** | Read tables, versions, and export CSV |
| **analyst** | All viewer permissions + create/edit tables, submit for approval |
| **admin** | All analyst permissions + approve/reject versions, manage users |
| **super_admin** | All admin permissions + manage tenants |

---

## Roadmap

### Phase 2: Usability
- [ ] Web frontend (SvelteKit + Tailwind)
- [ ] Bulk CSV import
- [ ] Email notifications for approval requests
- [ ] Column schema evolution (add/remove columns post-creation)

### Phase 3: Platform Expansion
- [ ] Extract versioning as standalone service
- [ ] Model Manager product (version control for actuarial models)
- [ ] Shared authentication service
- [ ] Audit logging dashboard

---

## Architecture Decisions

**Why PostgreSQL Row-Level Security?**  
Multi-tenant data isolation at the database level. Even if application code has bugs, one tenant physically cannot access another's data.

**Why a Raspberry Pi?**  
Cost (£80), fun, and proving that modern software doesn't need expensive cloud infrastructure for small-scale SaaS. Also great for demos – "This API you're hitting runs on a £80 computer in my house."

**Why API-first (no frontend yet)?**  
Actuaries are technical users who often prefer direct API access and CSV exports. A frontend is planned, but the product is fully functional via API and Swagger UI.

**Why version snapshots instead of Git integration?**  
Target users are fleeing Excel, not seeking Git. They need simple "save this version" semantics, not branches and merge conflicts. The architecture allows extracting versioning later if needed.

---

## Development Methodology: FADE

This project was built using FADE (Framework for Agentic Development and Engineering), a methodology for AI-assisted software development:

1. **PRDs define work units** – each feature is a JSON file with user stories and acceptance criteria
2. **AI agent implements autonomously** – Claude Code reads the PRD and builds the feature
3. **Human reviews outputs** – code review, testing, and direction-setting remain human tasks
4. **Context preserved between sessions** – FADE files maintain project state across AI sessions

The FADE framework is private, but the proof of concept is this working product.

---

## License

MIT License – see LICENSE file for details.

---

## Contact

**Steve Mitchell** – [@stevemitchelli](https://twitter.com/stevemitchelli)

Questions about agentic development? Drop me a line. Always happy to chat about AI-assisted engineering.
