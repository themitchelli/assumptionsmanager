from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user, TokenData
from schemas import (
    VersionCreate, VersionResponse, VersionListResponse,
    VersionDetailResponse, VersionRowResponse, TableDetailResponse,
    ColumnResponse, RowResponse, VersionDiffResponse, ModifiedCellResponse
)
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


@router.get("/{table_id}/versions/compare", response_model=VersionDiffResponse)
async def compare_versions(
    table_id: UUID,
    v1: UUID,
    v2: UUID,
    current_user: TokenData = Depends(get_current_user)
):
    """Compare two versions and return the differences"""
    if v1 == v2:
        raise HTTPException(
            status_code=400,
            detail="Cannot compare a version to itself"
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

            service = VersioningService(db)

            # Verify both versions exist and belong to this table
            version1 = service.get_version(v1)
            if not version1 or version1["table_id"] != table_id:
                raise HTTPException(status_code=404, detail="Version v1 not found")

            version2 = service.get_version(v2)
            if not version2 or version2["table_id"] != table_id:
                raise HTTPException(status_code=404, detail="Version v2 not found")

            # Compute the diff
            diff = service.compare_versions(v1, v2)

            return VersionDiffResponse(
                added_rows=diff["added_rows"],
                deleted_rows=diff["deleted_rows"],
                modified_cells=[
                    ModifiedCellResponse(
                        row_index=cell["row_index"],
                        column_name=cell["column_name"],
                        old_value=cell["old_value"],
                        new_value=cell["new_value"]
                    )
                    for cell in diff["modified_cells"]
                ]
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


@router.get("/{table_id}/versions/{version_id}", response_model=VersionDetailResponse)
async def get_version(
    table_id: UUID,
    version_id: UUID,
    current_user: TokenData = Depends(get_current_user)
):
    """Get a version snapshot with full data"""
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

            # Get version metadata
            service = VersioningService(db)
            version = service.get_version(version_id)

            if not version or version["table_id"] != table_id:
                raise HTTPException(status_code=404, detail="Version not found")

            # Get version cell data with typed values
            cells = service.get_version_data(version_id, table_id)

            # Group cells by row_index
            rows_dict: dict[int, dict[str, str | int | float | bool | None]] = {}
            for cell in cells:
                row_idx = cell["row_index"]
                if row_idx not in rows_dict:
                    rows_dict[row_idx] = {}
                rows_dict[row_idx][cell["column_name"]] = cell["value"]

            rows = [
                VersionRowResponse(row_index=idx, cells=cells)
                for idx, cells in sorted(rows_dict.items())
            ]

            return VersionDetailResponse(
                id=version["id"],
                version_number=version["version_number"],
                comment=version["comment"],
                created_by=version["created_by"],
                created_by_name=version.get("created_by_email"),
                created_at=version["created_at"],
                rows=rows
            )
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _cast_cell_value(value: str | None, data_type: str):
    """Cast cell value to appropriate Python type based on column data_type."""
    if value is None:
        return None
    if data_type == "integer":
        return int(value)
    elif data_type == "decimal":
        return float(value)
    elif data_type == "boolean":
        return value.lower() in ("true", "1", "yes")
    else:  # text, date
        return value


@router.post("/{table_id}/versions/{version_id}/restore", response_model=TableDetailResponse)
async def restore_version(
    table_id: UUID,
    version_id: UUID,
    current_user: TokenData = Depends(get_current_user)
):
    """Restore table data from a version snapshot"""
    if current_user.role not in WRITE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only analyst or admin can restore versions"
        )

    try:
        db = SessionLocal()
        try:
            # Verify table exists and belongs to tenant
            table_result = db.execute(
                text("""
                    SELECT id, tenant_id, name, description, effective_date,
                           created_by, created_at, updated_at
                    FROM assumption_tables
                    WHERE id = :table_id AND tenant_id = :tenant_id
                """),
                {"table_id": str(table_id), "tenant_id": str(current_user.tenant_id)}
            )
            table_row = table_result.fetchone()
            if not table_row:
                raise HTTPException(status_code=404, detail="Table not found")

            # Verify version exists and belongs to this table
            service = VersioningService(db)
            version = service.get_version(version_id)

            if not version or version["table_id"] != table_id:
                raise HTTPException(status_code=404, detail="Version not found")

            # Restore the version data
            service.restore_version(table_id, version_id)
            db.commit()

            # Fetch the restored table data to return
            # Get columns
            col_result = db.execute(
                text("""
                    SELECT id, name, data_type, position, created_at
                    FROM assumption_columns
                    WHERE table_id = :table_id
                    ORDER BY position
                """),
                {"table_id": str(table_id)}
            )
            columns = []
            column_types = {}
            column_names = {}
            for col_row in col_result:
                columns.append(ColumnResponse(
                    id=col_row[0],
                    name=col_row[1],
                    data_type=col_row[2],
                    position=col_row[3],
                    created_at=col_row[4]
                ))
                column_types[str(col_row[0])] = col_row[2]
                column_names[str(col_row[0])] = col_row[1]

            # Get rows with cells
            row_result = db.execute(
                text("""
                    SELECT r.id, r.row_index, c.column_id, c.value
                    FROM assumption_rows r
                    LEFT JOIN assumption_cells c ON c.row_id = r.id
                    WHERE r.table_id = :table_id
                    ORDER BY r.row_index, c.column_id
                """),
                {"table_id": str(table_id)}
            )

            rows_dict = {}
            for row in row_result:
                row_id = str(row[0])
                if row_id not in rows_dict:
                    rows_dict[row_id] = {
                        "id": row[0],
                        "row_index": row[1],
                        "cells": {}
                    }
                if row[2]:  # column_id exists
                    col_id = str(row[2])
                    col_name = column_names.get(col_id)
                    col_type = column_types.get(col_id, "text")
                    if col_name:
                        rows_dict[row_id]["cells"][col_name] = _cast_cell_value(row[3], col_type)

            rows = [
                RowResponse(
                    id=r["id"],
                    row_index=r["row_index"],
                    cells=r["cells"]
                )
                for r in sorted(rows_dict.values(), key=lambda x: x["row_index"])
            ]

            return TableDetailResponse(
                id=table_row[0],
                tenant_id=table_row[1],
                name=table_row[2],
                description=table_row[3],
                effective_date=str(table_row[4]) if table_row[4] else None,
                created_by=table_row[5],
                created_at=table_row[6],
                updated_at=table_row[7],
                columns=columns,
                rows=rows
            )
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{table_id}/versions/{version_id}", status_code=204)
async def delete_version(
    table_id: UUID,
    version_id: UUID,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete a version snapshot (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admin can delete versions"
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

            # Verify version exists and belongs to this table
            service = VersioningService(db)
            version = service.get_version(version_id)

            if not version or version["table_id"] != table_id:
                raise HTTPException(status_code=404, detail="Version not found")

            # Check if this is the only version
            version_count = service.count_versions(table_id)
            if version_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete the only version"
                )

            # Delete the version
            service.delete_version(version_id)
            db.commit()

            return None
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
