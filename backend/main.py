from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from database import engine
from routers import auth

app = FastAPI(title="Assumptions Manager", version="0.1.0")

app.include_router(auth.router)


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
async def list_tenants():
    """List all tenants (admin endpoint for demo)"""
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
