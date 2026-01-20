"""Export endpoints for assumption tables.

Provides CSV export functionality for:
- Current table state
- Specific version snapshots
- Latest approved version only
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user, TokenData
from services.export import CSVExportService

router = APIRouter(prefix="/tables", tags=["export"])

# 5 minute timeout for large exports
EXPORT_TIMEOUT = 300


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use in a filename."""
    safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._- ")
    sanitized = "".join(c if c in safe_chars else "_" for c in name)
    return sanitized.replace(" ", "_")


@router.get("/{table_id}/export/csv")
async def export_table_csv(
    table_id: UUID,
    include_metadata: bool = Query(default=False, description="Include metadata header rows prefixed with #"),
    approved_only: bool = Query(default=False, description="Export latest approved version instead of current state"),
    current_user: TokenData = Depends(get_current_user)
):
    """Export assumption table to CSV format.

    Query parameters:
    - include_metadata: If true, adds metadata rows prefixed with '#' at the top
    - approved_only: If true, exports the latest approved version instead of current table state

    All roles (viewer, analyst, admin) can export tables.
    """
    try:
        db = SessionLocal()
        try:
            # Verify table exists and belongs to tenant
            result = db.execute(
                text("""
                    SELECT id, name FROM assumption_tables
                    WHERE id = :table_id AND tenant_id = :tenant_id
                """),
                {"table_id": str(table_id), "tenant_id": str(current_user.tenant_id)}
            )
            table_row = result.fetchone()
            if not table_row:
                raise HTTPException(status_code=404, detail="Table not found")

            table_name = table_row[1]
            export_service = CSVExportService(db)

            if approved_only:
                # Find latest approved version
                approved_version = export_service.get_latest_approved_version(table_id)
                if not approved_version:
                    raise HTTPException(
                        status_code=404,
                        detail="No approved version exists for this table"
                    )

                version_number = approved_version["version_number"]
                filename = f"{sanitize_filename(table_name)}_v{version_number}.csv"

                # Stream version export
                content_generator = export_service.export_version(
                    table_id,
                    approved_version["id"],
                    include_metadata=include_metadata
                )
            else:
                # Export current table state
                filename = f"{sanitize_filename(table_name)}.csv"
                content_generator = export_service.export_table(
                    table_id,
                    include_metadata=include_metadata
                )

            return StreamingResponse(
                content_generator,
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
        finally:
            db.close()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{table_id}/versions/{version_id}/export/csv")
async def export_version_csv(
    table_id: UUID,
    version_id: UUID,
    include_metadata: bool = Query(default=False, description="Include metadata header rows prefixed with #"),
    current_user: TokenData = Depends(get_current_user)
):
    """Export a specific version snapshot to CSV format.

    Query parameters:
    - include_metadata: If true, adds metadata rows prefixed with '#' at the top
      including version number, created_by, created_at, and approval_status

    Works for all version statuses (draft, submitted, approved, rejected).
    All roles (viewer, analyst, admin) can export versions.
    """
    try:
        db = SessionLocal()
        try:
            # Verify table exists and belongs to tenant
            result = db.execute(
                text("""
                    SELECT id, name FROM assumption_tables
                    WHERE id = :table_id AND tenant_id = :tenant_id
                """),
                {"table_id": str(table_id), "tenant_id": str(current_user.tenant_id)}
            )
            table_row = result.fetchone()
            if not table_row:
                raise HTTPException(status_code=404, detail="Table not found")

            table_name = table_row[1]

            # Verify version exists and belongs to this table
            version_result = db.execute(
                text("""
                    SELECT v.id, v.version_number
                    FROM assumption_versions v
                    WHERE v.id = :version_id AND v.table_id = :table_id
                """),
                {"version_id": str(version_id), "table_id": str(table_id)}
            )
            version_row = version_result.fetchone()
            if not version_row:
                raise HTTPException(status_code=404, detail="Version not found")

            version_number = version_row[1]
            filename = f"{sanitize_filename(table_name)}_v{version_number}.csv"

            export_service = CSVExportService(db)

            # Stream version export
            content_generator = export_service.export_version(
                table_id,
                version_id,
                include_metadata=include_metadata
            )

            return StreamingResponse(
                content_generator,
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
        finally:
            db.close()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
