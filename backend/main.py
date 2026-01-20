from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import text

from database import engine
from routers import auth, users, tables, versions, export, imports
from auth import get_current_user, TokenData
from schemas import TenantCreate, TenantResponse, TenantUpdate
from uuid import UUID

app = FastAPI(title="Assumptions Manager", version="0.1.0")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tables.router)
app.include_router(versions.router)
app.include_router(export.router)
app.include_router(imports.router)


@app.get("/")
async def root():
    return {"message": "Hello from Assumptions Manager!", "status": "healthy"}


@app.get("/health")
async def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")


@app.get("/tenants")
async def list_tenants(current_user: TokenData = Depends(get_current_user)):
    """List all tenants (super_admin only)"""
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Only super_admin can access this endpoint"
        )
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, name, created_at FROM tenants"))
            tenants = [
                {"id": str(row[0]), "name": row[1], "created_at": str(row[2])}
                for row in result
            ]
        return {"tenants": tenants}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tenants", response_model=TenantResponse, status_code=201)
async def create_tenant(
    tenant: TenantCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """Create a new tenant (super_admin only)"""
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Only super_admin can access this endpoint"
        )
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("INSERT INTO tenants (name) VALUES (:name) RETURNING id, name, created_at"),
                {"name": tenant.name}
            )
            conn.commit()
            row = result.fetchone()
            return TenantResponse(id=row[0], name=row[1], created_at=row[2])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tenants/me", response_model=TenantResponse)
async def get_current_tenant(current_user: TokenData = Depends(get_current_user)):
    """Get the current user's tenant details (admin/super_admin only)"""
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=403,
            detail="Only admin can access tenant settings"
        )
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT id, name, created_at FROM tenants WHERE id = :tenant_id"),
                {"tenant_id": str(current_user.tenant_id)}
            )
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Tenant not found")
            return TenantResponse(id=row[0], name=row[1], created_at=row[2])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    update: TenantUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """Update tenant settings (admin can update own tenant, super_admin can update any)"""
    # Admin can only update their own tenant
    if current_user.role == "admin":
        if tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=403,
                detail="Admin can only update their own tenant"
            )
    elif current_user.role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Only admin or super_admin can update tenant settings"
        )

    # Build update query dynamically based on provided fields
    update_fields = []
    params = {"tenant_id": str(tenant_id)}

    if update.name is not None:
        update_fields.append("name = :name")
        params["name"] = update.name

    if not update_fields:
        raise HTTPException(
            status_code=400,
            detail="No fields to update"
        )

    update_fields.append("updated_at = NOW()")

    try:
        with engine.connect() as conn:
            # Check tenant exists
            check_result = conn.execute(
                text("SELECT id FROM tenants WHERE id = :tenant_id"),
                {"tenant_id": str(tenant_id)}
            )
            if not check_result.fetchone():
                raise HTTPException(status_code=404, detail="Tenant not found")

            # Update tenant
            query = f"UPDATE tenants SET {', '.join(update_fields)} WHERE id = :tenant_id RETURNING id, name, created_at"
            result = conn.execute(text(query), params)
            conn.commit()
            row = result.fetchone()
            return TenantResponse(id=row[0], name=row[1], created_at=row[2])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
