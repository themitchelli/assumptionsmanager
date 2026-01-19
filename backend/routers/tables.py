from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user, TokenData
from schemas import (
    TableCreate, TableResponse, TableListResponse, TableDetailResponse,
    ColumnResponse, RowResponse
)

router = APIRouter(prefix="/tables", tags=["tables"])

VALID_DATA_TYPES = {"text", "integer", "decimal", "date", "boolean"}
WRITE_ROLES = {"analyst", "admin"}


@router.get("", response_model=list[TableListResponse])
async def list_tables(current_user: TokenData = Depends(get_current_user)):
    """List all assumption tables in the current tenant"""
    try:
        db = SessionLocal()
        try:
            result = db.execute(
                text("""
                    SELECT id, name, description, effective_date, created_by, created_at
                    FROM assumption_tables
                    WHERE tenant_id = :tenant_id
                    ORDER BY created_at DESC
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
                    created_at=row[5]
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
