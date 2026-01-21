from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user, TokenData
from schemas import (
    TableCreate, TableUpdate, TableResponse, TableListResponse, TableDetailResponse,
    ColumnCreate, ColumnResponse, RowResponse, RowsCreate, RowUpdate
)

router = APIRouter(prefix="/tables", tags=["tables"])

VALID_DATA_TYPES = {"text", "integer", "decimal", "date", "boolean"}
WRITE_ROLES = {"analyst", "admin", "super_admin"}


@router.get("", response_model=list[TableListResponse])
async def list_tables(current_user: TokenData = Depends(get_current_user)):
    """List all assumption tables in the current tenant with column/row counts"""
    try:
        db = SessionLocal()
        try:
            result = db.execute(
                text("""
                    SELECT
                        t.id,
                        t.name,
                        t.description,
                        t.effective_date,
                        t.created_by,
                        t.created_at,
                        t.updated_at,
                        COALESCE(col.column_count, 0) AS column_count,
                        COALESCE(r.row_count, 0) AS row_count
                    FROM assumption_tables t
                    LEFT JOIN (
                        SELECT table_id, COUNT(*) AS column_count
                        FROM assumption_columns
                        GROUP BY table_id
                    ) col ON col.table_id = t.id
                    LEFT JOIN (
                        SELECT table_id, COUNT(*) AS row_count
                        FROM assumption_rows
                        GROUP BY table_id
                    ) r ON r.table_id = t.id
                    WHERE t.tenant_id = :tenant_id
                    ORDER BY t.created_at DESC
                """),
                {"tenant_id": str(current_user.tenant_id)}
            )
            tables = [
                TableListResponse(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    effective_date=str(row[3]) if row[3] else None,
                    created_by=row[4],
                    created_at=row[5],
                    updated_at=row[6],
                    column_count=row[7],
                    row_count=row[8]
                )
                for row in result
            ]
            return tables
        finally:
            db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def cast_cell_value(value: str | None, data_type: str):
    """Cast cell value to appropriate Python type based on column data_type"""
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


@router.get("/{table_id}", response_model=TableDetailResponse)
async def get_table(
    table_id: UUID,
    current_user: TokenData = Depends(get_current_user)
):
    """Get a complete assumption table including all rows and cells"""
    try:
        db = SessionLocal()
        try:
            # Fetch table with tenant check
            result = db.execute(
                text("""
                    SELECT id, tenant_id, name, description, effective_date, created_by, created_at, updated_at
                    FROM assumption_tables
                    WHERE id = :table_id AND tenant_id = :tenant_id
                """),
                {"table_id": str(table_id), "tenant_id": str(current_user.tenant_id)}
            )
            table_row = result.fetchone()

            if not table_row:
                raise HTTPException(status_code=404, detail="Table not found")

            # Fetch columns
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
            column_types = {}  # column_id -> data_type mapping
            column_names = {}  # column_id -> name mapping
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

            # Fetch rows with cells
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

            # Group cells by row
            rows_dict = {}
            for row in row_result:
                row_id = str(row[0])
                if row_id not in rows_dict:
                    rows_dict[row_id] = {
                        "id": row[0],
                        "row_index": row[1],
                        "cells": {}
                    }
                if row[2]:  # column_id exists (has cell data)
                    col_id = str(row[2])
                    col_name = column_names.get(col_id)
                    col_type = column_types.get(col_id, "text")
                    if col_name:
                        rows_dict[row_id]["cells"][col_name] = cast_cell_value(row[3], col_type)

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


@router.post("/{table_id}/columns", response_model=ColumnResponse, status_code=201)
async def add_column(
    table_id: UUID,
    column: ColumnCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """Add a column to an existing assumption table"""
    if current_user.role not in WRITE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only analyst or admin can add columns"
        )

    # Validate data type
    if column.data_type not in VALID_DATA_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data_type '{column.data_type}'. Must be one of: {', '.join(VALID_DATA_TYPES)}"
        )

    # Validate column name - no special characters, reasonable length
    name = column.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Column name is required")
    if len(name) > 100:
        raise HTTPException(status_code=400, detail="Column name must be 100 characters or less")
    # Allow alphanumeric, underscores, and spaces
    import re
    if not re.match(r'^[\w\s]+$', name):
        raise HTTPException(
            status_code=400,
            detail="Column name can only contain letters, numbers, underscores, and spaces"
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

            # Check for duplicate column name
            dup_result = db.execute(
                text("""
                    SELECT id FROM assumption_columns
                    WHERE table_id = :table_id AND LOWER(name) = LOWER(:name)
                """),
                {"table_id": str(table_id), "name": name}
            )
            if dup_result.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail=f"A column with name '{name}' already exists in this table"
                )

            # Get the next position (append to right side of grid)
            max_result = db.execute(
                text("""
                    SELECT COALESCE(MAX(position), -1) FROM assumption_columns
                    WHERE table_id = :table_id
                """),
                {"table_id": str(table_id)}
            )
            next_position = max_result.fetchone()[0] + 1

            # Insert the column
            col_result = db.execute(
                text("""
                    INSERT INTO assumption_columns (table_id, name, data_type, position)
                    VALUES (:table_id, :name, :data_type, :position)
                    RETURNING id, name, data_type, position, created_at
                """),
                {
                    "table_id": str(table_id),
                    "name": name,
                    "data_type": column.data_type,
                    "position": next_position
                }
            )
            row = col_result.fetchone()

            # Update table's updated_at timestamp
            db.execute(
                text("UPDATE assumption_tables SET updated_at = NOW() WHERE id = :table_id"),
                {"table_id": str(table_id)}
            )

            db.commit()

            return ColumnResponse(
                id=row[0],
                name=row[1],
                data_type=row[2],
                position=row[3],
                created_at=row[4]
            )
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{table_id}", response_model=TableListResponse)
async def update_table(
    table_id: UUID,
    update: TableUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """Update table metadata (name, description, effective_date)"""
    if current_user.role not in WRITE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only analyst or admin can update tables"
        )

    # Validate effective_date format if provided
    effective_date_value = None
    if update.effective_date is not None:
        try:
            effective_date_value = date.fromisoformat(update.effective_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid effective_date format. Use YYYY-MM-DD"
            )

    try:
        db = SessionLocal()
        try:
            # Check table exists and belongs to tenant
            result = db.execute(
                text("""
                    SELECT id, name, description, effective_date, created_by, created_at
                    FROM assumption_tables
                    WHERE id = :table_id AND tenant_id = :tenant_id
                """),
                {"table_id": str(table_id), "tenant_id": str(current_user.tenant_id)}
            )
            existing = result.fetchone()

            if not existing:
                raise HTTPException(status_code=404, detail="Table not found")

            # Build dynamic update query
            updates = []
            params = {"table_id": str(table_id)}

            if update.name is not None:
                updates.append("name = :name")
                params["name"] = update.name
            if update.description is not None:
                updates.append("description = :description")
                params["description"] = update.description
            if update.effective_date is not None:
                updates.append("effective_date = :effective_date")
                params["effective_date"] = effective_date_value

            if not updates:
                # No updates provided, return existing
                return TableListResponse(
                    id=existing[0],
                    name=existing[1],
                    description=existing[2],
                    effective_date=str(existing[3]) if existing[3] else None,
                    created_by=existing[4],
                    created_at=existing[5]
                )

            updates.append("updated_at = NOW()")
            update_sql = f"UPDATE assumption_tables SET {', '.join(updates)} WHERE id = :table_id RETURNING id, name, description, effective_date, created_by, created_at"

            result = db.execute(text(update_sql), params)
            row = result.fetchone()
            db.commit()

            return TableListResponse(
                id=row[0],
                name=row[1],
                description=row[2],
                effective_date=str(row[3]) if row[3] else None,
                created_by=row[4],
                created_at=row[5]
            )
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{table_id}", status_code=204)
async def delete_table(
    table_id: UUID,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete an assumption table and all its data"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admin can delete tables"
        )

    try:
        db = SessionLocal()
        try:
            # Check table exists and belongs to tenant
            result = db.execute(
                text("""
                    SELECT id FROM assumption_tables
                    WHERE id = :table_id AND tenant_id = :tenant_id
                """),
                {"table_id": str(table_id), "tenant_id": str(current_user.tenant_id)}
            )
            existing = result.fetchone()

            if not existing:
                raise HTTPException(status_code=404, detail="Table not found")

            # Delete table (cascades to columns, rows, cells)
            db.execute(
                text("DELETE FROM assumption_tables WHERE id = :table_id"),
                {"table_id": str(table_id)}
            )
            db.commit()

            return None
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def validate_cell_value(value, data_type: str, column_name: str) -> str | None:
    """Validate and convert cell value to string for storage. Returns None for null values."""
    if value is None:
        return None

    try:
        if data_type == "integer":
            int(value)
            return str(int(value))
        elif data_type == "decimal":
            float(value)
            return str(float(value))
        elif data_type == "boolean":
            if isinstance(value, bool):
                return str(value).lower()
            if isinstance(value, str) and value.lower() in ("true", "false", "1", "0", "yes", "no"):
                return "true" if value.lower() in ("true", "1", "yes") else "false"
            raise ValueError("Invalid boolean")
        elif data_type == "date":
            # Validate date format
            date.fromisoformat(str(value))
            return str(value)
        else:  # text
            return str(value)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid value '{value}' for column '{column_name}' (expected {data_type})"
        )


@router.post("/{table_id}/rows", response_model=list[RowResponse], status_code=201)
async def add_rows(
    table_id: UUID,
    data: RowsCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """Add one or more rows to an assumption table"""
    if current_user.role not in WRITE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only analyst or admin can add rows"
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

            # Get column definitions for validation
            col_result = db.execute(
                text("""
                    SELECT id, name, data_type FROM assumption_columns
                    WHERE table_id = :table_id
                """),
                {"table_id": str(table_id)}
            )
            columns = {row[1]: {"id": row[0], "data_type": row[2]} for row in col_result}

            if not columns:
                raise HTTPException(
                    status_code=400,
                    detail="Table has no columns defined"
                )

            # Get the next row_index
            max_result = db.execute(
                text("""
                    SELECT COALESCE(MAX(row_index), -1) FROM assumption_rows
                    WHERE table_id = :table_id
                """),
                {"table_id": str(table_id)}
            )
            next_index = max_result.fetchone()[0] + 1

            created_rows = []

            for row_data in data.rows:
                # Validate all cell values and column names
                validated_cells = {}
                for col_name, value in row_data.cells.items():
                    if col_name not in columns:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Unknown column '{col_name}'"
                        )
                    validated_cells[col_name] = validate_cell_value(
                        value, columns[col_name]["data_type"], col_name
                    )

                # Insert row
                row_result = db.execute(
                    text("""
                        INSERT INTO assumption_rows (table_id, row_index)
                        VALUES (:table_id, :row_index)
                        RETURNING id, row_index
                    """),
                    {"table_id": str(table_id), "row_index": next_index}
                )
                row = row_result.fetchone()
                row_id = row[0]
                row_index = row[1]

                # Insert cells
                cells_response = {}
                for col_name, value in validated_cells.items():
                    db.execute(
                        text("""
                            INSERT INTO assumption_cells (row_id, column_id, value)
                            VALUES (:row_id, :column_id, :value)
                        """),
                        {
                            "row_id": str(row_id),
                            "column_id": str(columns[col_name]["id"]),
                            "value": value
                        }
                    )
                    # Cast back for response
                    cells_response[col_name] = cast_cell_value(value, columns[col_name]["data_type"])

                created_rows.append(RowResponse(
                    id=row_id,
                    row_index=row_index,
                    cells=cells_response
                ))
                next_index += 1

            db.commit()
            return created_rows
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{table_id}/rows/{row_id}", response_model=RowResponse)
async def update_row(
    table_id: UUID,
    row_id: UUID,
    data: RowUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """Update cell values in an existing row"""
    if current_user.role not in WRITE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only analyst or admin can update rows"
        )

    try:
        db = SessionLocal()
        try:
            # Verify table exists and belongs to tenant
            table_result = db.execute(
                text("""
                    SELECT id FROM assumption_tables
                    WHERE id = :table_id AND tenant_id = :tenant_id
                """),
                {"table_id": str(table_id), "tenant_id": str(current_user.tenant_id)}
            )
            if not table_result.fetchone():
                raise HTTPException(status_code=404, detail="Table not found")

            # Verify row exists and belongs to this table
            row_result = db.execute(
                text("""
                    SELECT id, row_index FROM assumption_rows
                    WHERE id = :row_id AND table_id = :table_id
                """),
                {"row_id": str(row_id), "table_id": str(table_id)}
            )
            row = row_result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Row not found")

            row_index = row[1]

            # Get column definitions for validation
            col_result = db.execute(
                text("""
                    SELECT id, name, data_type FROM assumption_columns
                    WHERE table_id = :table_id
                """),
                {"table_id": str(table_id)}
            )
            columns = {r[1]: {"id": r[0], "data_type": r[2]} for r in col_result}

            # Validate and update cells
            for col_name, value in data.cells.items():
                if col_name not in columns:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unknown column '{col_name}'"
                    )

                validated_value = validate_cell_value(
                    value, columns[col_name]["data_type"], col_name
                )

                # Upsert cell (insert or update)
                db.execute(
                    text("""
                        INSERT INTO assumption_cells (row_id, column_id, value)
                        VALUES (:row_id, :column_id, :value)
                        ON CONFLICT (row_id, column_id)
                        DO UPDATE SET value = EXCLUDED.value
                    """),
                    {
                        "row_id": str(row_id),
                        "column_id": str(columns[col_name]["id"]),
                        "value": validated_value
                    }
                )

            db.commit()

            # Fetch all cells for the row to return complete response
            cells_result = db.execute(
                text("""
                    SELECT ac.name, acel.value, ac.data_type
                    FROM assumption_cells acel
                    JOIN assumption_columns ac ON ac.id = acel.column_id
                    WHERE acel.row_id = :row_id
                """),
                {"row_id": str(row_id)}
            )
            cells = {
                r[0]: cast_cell_value(r[1], r[2])
                for r in cells_result
            }

            return RowResponse(
                id=row_id,
                row_index=row_index,
                cells=cells
            )
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{table_id}/rows/{row_id}", status_code=204)
async def delete_row(
    table_id: UUID,
    row_id: UUID,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete a row and all its cells"""
    if current_user.role not in WRITE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only analyst or admin can delete rows"
        )

    try:
        db = SessionLocal()
        try:
            # Verify table exists and belongs to tenant
            table_result = db.execute(
                text("""
                    SELECT id FROM assumption_tables
                    WHERE id = :table_id AND tenant_id = :tenant_id
                """),
                {"table_id": str(table_id), "tenant_id": str(current_user.tenant_id)}
            )
            if not table_result.fetchone():
                raise HTTPException(status_code=404, detail="Table not found")

            # Verify row exists and belongs to this table
            row_result = db.execute(
                text("""
                    SELECT id FROM assumption_rows
                    WHERE id = :row_id AND table_id = :table_id
                """),
                {"row_id": str(row_id), "table_id": str(table_id)}
            )
            if not row_result.fetchone():
                raise HTTPException(status_code=404, detail="Row not found")

            # Delete row (cascades to cells via FK constraint)
            db.execute(
                text("DELETE FROM assumption_rows WHERE id = :row_id"),
                {"row_id": str(row_id)}
            )
            db.commit()

            return None
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=TableResponse, status_code=201)
async def create_table(
    table: TableCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """Create a new assumption table with column definitions"""
    if current_user.role not in WRITE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only analyst or admin can create tables"
        )

    # Validate column data types
    for col in table.columns:
        if col.data_type not in VALID_DATA_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid data_type '{col.data_type}' for column '{col.name}'. Must be one of: {', '.join(VALID_DATA_TYPES)}"
            )

    # Validate effective_date format if provided
    effective_date_value = None
    if table.effective_date:
        try:
            effective_date_value = date.fromisoformat(table.effective_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid effective_date format. Use YYYY-MM-DD"
            )

    try:
        db = SessionLocal()
        try:
            # Insert assumption table
            result = db.execute(
                text("""
                    INSERT INTO assumption_tables (tenant_id, name, description, effective_date, created_by)
                    VALUES (:tenant_id, :name, :description, :effective_date, :created_by)
                    RETURNING id, tenant_id, name, description, effective_date, created_by, created_at, updated_at
                """),
                {
                    "tenant_id": str(current_user.tenant_id),
                    "name": table.name,
                    "description": table.description,
                    "effective_date": effective_date_value,
                    "created_by": str(current_user.user_id)
                }
            )
            row = result.fetchone()
            table_id = row[0]

            # Insert columns
            columns = []
            for col in table.columns:
                col_result = db.execute(
                    text("""
                        INSERT INTO assumption_columns (table_id, name, data_type, position)
                        VALUES (:table_id, :name, :data_type, :position)
                        RETURNING id, name, data_type, position, created_at
                    """),
                    {
                        "table_id": str(table_id),
                        "name": col.name,
                        "data_type": col.data_type,
                        "position": col.position
                    }
                )
                col_row = col_result.fetchone()
                columns.append(ColumnResponse(
                    id=col_row[0],
                    name=col_row[1],
                    data_type=col_row[2],
                    position=col_row[3],
                    created_at=col_row[4]
                ))

            db.commit()

            return TableResponse(
                id=row[0],
                tenant_id=row[1],
                name=row[2],
                description=row[3],
                effective_date=str(row[4]) if row[4] else None,
                created_by=row[5],
                created_at=row[6],
                updated_at=row[7],
                columns=columns
            )
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
