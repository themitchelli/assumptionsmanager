from uuid import UUID
import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user, TokenData
from schemas import (
    VersionCreate, VersionResponse, VersionListResponse,
    VersionDetailResponse, VersionRowResponse, TableDetailResponse,
    ColumnResponse, RowResponse, VersionDiffResponse, ModifiedCellResponse,
    FormattedDiffResponse, VersionMetadata, DiffSummary, ColumnSummary,
    CellStatus, RowChange
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


@router.get("/{table_id}/versions/diff", response_model=FormattedDiffResponse)
async def get_formatted_diff(
    table_id: UUID,
    v1: UUID,
    v2: UUID,
    columns: str | None = None,
    row_start: int | None = None,
    row_end: int | None = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Get a formatted diff between two versions with full context for visual comparison.

    Query parameters:
    - v1: First version ID (older)
    - v2: Second version ID (newer)
    - columns: Optional comma-separated list of column names to filter
    - row_start: Optional start row index (inclusive)
    - row_end: Optional end row index (inclusive)
    """
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

            # Parse columns filter
            columns_filter = None
            if columns:
                columns_filter = [c.strip() for c in columns.split(",") if c.strip()]
                # Validate column names exist
                valid_columns = service.get_all_column_names(table_id)
                invalid_columns = [c for c in columns_filter if c not in valid_columns]
                if invalid_columns:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid column names: {', '.join(invalid_columns)}"
                    )

            # Get formatted diff
            diff = service.get_formatted_diff(
                v1, v2,
                columns_filter=columns_filter,
                row_start=row_start,
                row_end=row_end
            )

            # Build response
            return FormattedDiffResponse(
                table_id=diff["table_id"],
                version_a=VersionMetadata(**diff["version_a"]),
                version_b=VersionMetadata(**diff["version_b"]),
                summary=DiffSummary(**diff["summary"]),
                column_summary=[ColumnSummary(**cs) for cs in diff["column_summary"]],
                changes=[
                    RowChange(
                        type=change["type"],
                        row_index=change["row_index"],
                        cells=[CellStatus(**cell) for cell in change["cells"]]
                    )
                    for change in diff["changes"]
                ]
            )
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{table_id}/versions/diff/export")
async def export_diff_csv(
    table_id: UUID,
    v1: UUID,
    v2: UUID,
    format: str = "csv",
    columns: str | None = None,
    row_start: int | None = None,
    row_end: int | None = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Export diff between two versions as CSV for offline review or audit.

    Query parameters:
    - v1: First version ID (older)
    - v2: Second version ID (newer)
    - format: Export format (currently only 'csv' supported)
    - columns: Optional comma-separated list of column names to filter
    - row_start: Optional start row index (inclusive)
    - row_end: Optional end row index (inclusive)
    """
    if format != "csv":
        raise HTTPException(
            status_code=400,
            detail="Only 'csv' format is currently supported"
        )

    if v1 == v2:
        raise HTTPException(
            status_code=400,
            detail="Cannot compare a version to itself"
        )

    try:
        db = SessionLocal()
        try:
            # Verify table exists and get its name
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

            service = VersioningService(db)

            # Verify both versions exist and belong to this table
            version1 = service.get_version(v1)
            if not version1 or version1["table_id"] != table_id:
                raise HTTPException(status_code=404, detail="Version v1 not found")

            version2 = service.get_version(v2)
            if not version2 or version2["table_id"] != table_id:
                raise HTTPException(status_code=404, detail="Version v2 not found")

            # Parse columns filter
            columns_filter = None
            if columns:
                columns_filter = [c.strip() for c in columns.split(",") if c.strip()]
                valid_columns = service.get_all_column_names(table_id)
                invalid_columns = [c for c in columns_filter if c not in valid_columns]
                if invalid_columns:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid column names: {', '.join(invalid_columns)}"
                    )

            # Get formatted diff
            diff = service.get_formatted_diff(
                v1, v2,
                columns_filter=columns_filter,
                row_start=row_start,
                row_end=row_end
            )

            # Generate CSV
            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(["row_index", "column_name", "old_value", "new_value", "change_type"])

            # Write changes
            for change in diff["changes"]:
                row_idx = change["row_index"]
                change_type = change["type"]

                for cell in change["cells"]:
                    col_name = cell["column_name"]
                    status = cell["status"]

                    if status == "unchanged":
                        continue  # Don't include unchanged cells in export

                    if change_type == "row_added":
                        old_val = ""
                        new_val = cell.get("value", "")
                    elif change_type == "row_removed":
                        old_val = cell.get("value", "")
                        new_val = ""
                    else:  # row_modified
                        old_val = cell.get("old_value", "")
                        new_val = cell.get("new_value", "")

                    writer.writerow([row_idx, col_name, old_val, new_val, status])

            # Prepare response
            output.seek(0)

            # Generate filename
            v1_num = version1["version_number"]
            v2_num = version2["version_number"]
            # Sanitize table name for filename
            safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in table_name)
            safe_name = safe_name.replace(" ", "_")
            filename = f"{safe_name}_diff_v{v1_num}_to_v{v2_num}.csv"

            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
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
                rows=rows,
                approval_status=version.get("approval_status", "draft"),
                submitted_by=version.get("submitted_by"),
                submitted_at=version.get("submitted_at"),
                reviewed_by=version.get("reviewed_by"),
                reviewed_at=version.get("reviewed_at")
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
