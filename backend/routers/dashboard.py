"""Dashboard statistics endpoint"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from database import engine
from auth import get_current_user, TokenData
from schemas import DashboardStatsResponse


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(current_user: TokenData = Depends(get_current_user)):
    """Get dashboard statistics for the current user's tenant.

    Returns:
        - table_count: Total assumption tables in tenant
        - recent_activity_count: Tables updated in last 7 days
        - version_count: Total version snapshots across all tables
    """
    tenant_id = str(current_user.tenant_id)

    try:
        with engine.connect() as conn:
            # Count assumption tables for tenant
            table_result = conn.execute(
                text("SELECT COUNT(*) FROM assumption_tables WHERE tenant_id = :tenant_id"),
                {"tenant_id": tenant_id}
            )
            table_count = table_result.fetchone()[0]

            # Count tables updated in last 7 days
            recent_result = conn.execute(
                text("""
                    SELECT COUNT(*) FROM assumption_tables
                    WHERE tenant_id = :tenant_id
                    AND updated_at >= NOW() - INTERVAL '7 days'
                """),
                {"tenant_id": tenant_id}
            )
            recent_activity_count = recent_result.fetchone()[0]

            # Count all version snapshots across tenant's tables
            version_result = conn.execute(
                text("""
                    SELECT COUNT(*) FROM assumption_versions av
                    JOIN assumption_tables at ON av.table_id = at.id
                    WHERE at.tenant_id = :tenant_id
                """),
                {"tenant_id": tenant_id}
            )
            version_count = version_result.fetchone()[0]

        return DashboardStatsResponse(
            table_count=table_count,
            recent_activity_count=recent_activity_count,
            version_count=version_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
