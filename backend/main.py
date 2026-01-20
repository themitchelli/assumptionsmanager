from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import text

from database import engine
from routers import auth, users, tables, versions
from auth import get_current_user, TokenData
from schemas import TenantCreate, TenantResponse

app = FastAPI(title="Assumptions Manager", version="0.1.0")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tables.router)
app.include_router(versions.router)


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
