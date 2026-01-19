from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user, TokenData
from schemas import TableCreate, TableResponse, TableListResponse, ColumnResponse

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
