from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user, TokenData
from schemas import VersionCreate, VersionResponse, VersionListResponse
from services.versioning import VersioningService

router = APIRouter(prefix="/tables", tags=["versions"])

WRITE_ROLES = {"analyst", "admin"}


@router.post("/{table_id}/versions", response_model=VersionResponse, status_code=201)
async def create_version(
    table_id: UUID,
    data: VersionCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """Create a version snapshot of the current table state"""
    if current_user.role not in WRITE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only analyst or admin can create versions"
        )

    # Validate comment length
    if len(data.comment) > 500:
        raise HTTPException(
            status_code=400,
            detail="Comment must be 500 characters or less"
        )

    try:
        db = SessionLocal()
        try:
            # Verify table exists and belongs to tenant
            result = db.execute(
                text("""
                    SELECT id FROM assumption_tables
                    WHERE id = :table_id AND tenant_id = :tenant_id
                """),
                {"table_id": str(table_id), "tenant_id": str(current_user.tenant_id)}
            )
            if not result.fetchone():
                raise HTTPException(status_code=404, detail="Table not found")

            # Create version snapshot
            service = VersioningService(db)
            version = service.create_snapshot(
                entity_type="assumption_table",
                entity_id=table_id,
                user_id=current_user.user_id,
                comment=data.comment
            )

            db.commit()

            return VersionResponse(
                id=version["id"],
                version_number=version["version_number"],
                comment=version["comment"],
                created_by=version["created_by"],
                created_at=version["created_at"]
            )
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{table_id}/versions", response_model=list[VersionListResponse])
async def list_versions(
    table_id: UUID,
    current_user: TokenData = Depends(get_current_user)
):
    """List all versions of a table, newest first"""
    try:
        db = SessionLocal()
        try:
            # Verify table exists and belongs to tenant
            result = db.execute(
                text("""
                    SELECT id FROM assumption_tables
                    WHERE id = :table_id AND tenant_id = :tenant_id
                """),
                {"table_id": str(table_id), "tenant_id": str(current_user.tenant_id)}
            )
            if not result.fetchone():
                raise HTTPException(status_code=404, detail="Table not found")

            service = VersioningService(db)
            versions = service.list_versions(table_id)

            return [
                VersionListResponse(
                    id=v["id"],
                    version_number=v["version_number"],
                    comment=v["comment"],
                    created_by=v["created_by"],
                    created_by_name=v["created_by_name"],
                    created_at=v["created_at"]
                )
                for v in versions
            ]
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
