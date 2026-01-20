from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import text

from database import engine
from routers import auth, users, tables, versions, export, imports
from auth import get_current_user, TokenData, hash_password
from schemas import TenantCreate, TenantResponse, TenantUpdate, TenantListResponse, TenantListItemResponse, PlatformStatsResponse, TenantDetailResponse, TenantCreateWithAdmin, TenantCreateResponse
import secrets
import string
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


@app.get("/tenants", response_model=TenantListResponse)
async def list_tenants(current_user: TokenData = Depends(get_current_user)):
    """List all tenants with user counts (super_admin only)"""
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Only super_admin can access this endpoint"
        )
    try:
        with engine.connect() as conn:
            # Get tenants with user counts via LEFT JOIN
            result = conn.execute(text("""
                SELECT t.id, t.name, t.created_at, COUNT(u.id) as user_count
                FROM tenants t
                LEFT JOIN users u ON u.tenant_id = t.id
                GROUP BY t.id, t.name, t.created_at
                ORDER BY t.created_at DESC
            """))
            tenants = [
                TenantListItemResponse(
                    id=row[0],
                    name=row[1],
                    created_at=row[2],
                    user_count=row[3],
                    status="active"  # All tenants are active for now (deactivation in US-008)
                )
                for row in result
            ]
        return TenantListResponse(tenants=tenants)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tenants/stats", response_model=PlatformStatsResponse)
async def get_platform_stats(current_user: TokenData = Depends(get_current_user)):
    """Get platform-wide statistics (super_admin only)"""
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Only super_admin can access this endpoint"
        )
    try:
        with engine.connect() as conn:
            # Get tenant count
            tenant_result = conn.execute(text("SELECT COUNT(*) FROM tenants"))
            total_tenants = tenant_result.fetchone()[0]

            # Get user count
            user_result = conn.execute(text("SELECT COUNT(*) FROM users"))
            total_users = user_result.fetchone()[0]

            # For now, all tenants are active (deactivation feature in US-008)
            active_tenants = total_tenants

        return PlatformStatsResponse(
            total_tenants=total_tenants,
            active_tenants=active_tenants,
            total_users=total_users
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tenants/{tenant_id}", response_model=TenantDetailResponse)
async def get_tenant(
    tenant_id: UUID,
    current_user: TokenData = Depends(get_current_user)
):
    """Get a single tenant with details (super_admin only)"""
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Only super_admin can access this endpoint"
        )
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT t.id, t.name, t.created_at, t.updated_at, COUNT(u.id) as user_count
                FROM tenants t
                LEFT JOIN users u ON u.tenant_id = t.id
                WHERE t.id = :tenant_id
                GROUP BY t.id, t.name, t.created_at, t.updated_at
            """), {"tenant_id": str(tenant_id)})
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Tenant not found")
            return TenantDetailResponse(
                id=row[0],
                name=row[1],
                created_at=row[2],
                updated_at=row[3],
                user_count=row[4],
                status="active"  # All tenants are active for now (deactivation in US-008)
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def generate_temp_password(length: int = 16) -> str:
    """Generate a secure temporary password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@app.post("/tenants", response_model=TenantCreateResponse, status_code=201)
async def create_tenant(
    tenant: TenantCreateWithAdmin,
    current_user: TokenData = Depends(get_current_user)
):
    """Create a new tenant with initial admin user (super_admin only).

    Creates the tenant and an admin user in a single transaction.
    In production, the admin would receive an email with login instructions.
    """
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Only super_admin can create tenants"
        )

    # Validate tenant name length
    if len(tenant.name.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="Tenant name must be at least 2 characters"
        )
    if len(tenant.name) > 100:
        raise HTTPException(
            status_code=400,
            detail="Tenant name must be less than 100 characters"
        )

    try:
        with engine.connect() as conn:
            # Check tenant name uniqueness
            name_check = conn.execute(
                text("SELECT id FROM tenants WHERE LOWER(name) = LOWER(:name)"),
                {"name": tenant.name.strip()}
            )
            if name_check.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail="A tenant with this name already exists"
                )

            # Check admin email uniqueness (globally, not just within tenant)
            email_check = conn.execute(
                text("SELECT id FROM users WHERE LOWER(email) = LOWER(:email)"),
                {"email": tenant.admin_email}
            )
            if email_check.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail="A user with this email already exists"
                )

            # Create tenant
            tenant_result = conn.execute(
                text("INSERT INTO tenants (name) VALUES (:name) RETURNING id, name, created_at"),
                {"name": tenant.name.strip()}
            )
            tenant_row = tenant_result.fetchone()
            tenant_id = tenant_row[0]

            # Generate temporary password and create admin user
            temp_password = generate_temp_password()
            password_hash = hash_password(temp_password)

            user_result = conn.execute(
                text("""
                    INSERT INTO users (tenant_id, email, password_hash, role)
                    VALUES (:tenant_id, :email, :password_hash, 'admin')
                    RETURNING id, email
                """),
                {
                    "tenant_id": str(tenant_id),
                    "email": tenant.admin_email,
                    "password_hash": password_hash
                }
            )
            user_row = user_result.fetchone()

            conn.commit()

            # Note: In production, send welcome email to admin_email with temp_password
            # or a password reset link

            return TenantCreateResponse(
                id=tenant_row[0],
                name=tenant_row[1],
                created_at=tenant_row[2],
                admin_id=user_row[0],
                admin_email=user_row[1]
            )
    except HTTPException:
        raise
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
