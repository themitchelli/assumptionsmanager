"""Import endpoints for assumption tables.

Provides CSV import functionality for:
- Creating new tables from CSV
- Replacing existing table data
- Appending rows to existing tables
- Previewing imports before committing
"""
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import text

from database import SessionLocal
from auth import get_current_user, TokenData
from schemas import (
    ImportPreviewResponse,
    ImportResultResponse,
    ImportReplaceResultResponse,
    ImportAppendResultResponse,
    InferredColumn,
    ImportValidationError
)
from services.csv_import import CSVImportService

router = APIRouter(prefix="/tables", tags=["import"])

WRITE_ROLES = {"analyst", "admin", "super_admin"}

# 5 minute timeout for large imports
IMPORT_TIMEOUT = 300


def _raise_value_error(e: ValueError):
    """Convert ValueError to appropriate HTTP exception.

    Returns 413 Payload Too Large for file size errors,
    400 Bad Request for other validation errors.
    """
    error_msg = str(e)
    if "exceeds maximum" in error_msg.lower():
        raise HTTPException(status_code=413, detail=error_msg)
    raise HTTPException(status_code=400, detail=error_msg)


@router.post("/import/csv", response_model=ImportResultResponse, status_code=201)
async def create_table_from_csv(
    file: UploadFile = File(...),
    table_name: str = Form(...),
    description: str | None = Form(default=None),
    effective_date: str | None = Form(default=None),
    column_types: str | None = Form(default=None, description="JSON object mapping column names to types"),
    current_user: TokenData = Depends(get_current_user)
):
    """Create a new assumption table from a CSV file.

    The first row of the CSV is treated as column headers.
    Subsequent rows become the table data.

    Column data types are inferred automatically:
    - integer: All values match ^-?\\d+$
    - decimal: All values are numeric with optional decimal point
    - date: All values match YYYY-MM-DD format
    - boolean: All values in [true, false, yes, no, 1, 0]
    - text: Default fallback

    You can override inferred types with the column_types parameter.

    Requires analyst or admin role.
    """
    if current_user.role not in WRITE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only analyst or admin can import tables"
        )

    # Parse column_types if provided
    parsed_column_types = None
    if column_types:
        try:
            import json
            parsed_column_types = json.loads(column_types)
            if not isinstance(parsed_column_types, dict):
                raise ValueError("column_types must be a JSON object")
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid column_types JSON: {str(e)}"
            )

    try:
        db = SessionLocal()
        try:
            import_service = CSVImportService(db)

            result = import_service.create_table_from_csv(
                file=file.file,
                table_name=table_name,
                tenant_id=current_user.tenant_id,
                created_by=current_user.user_id,
                description=description,
                effective_date=effective_date,
                column_types=parsed_column_types
            )

            return ImportResultResponse(
                table_id=result.table_id,
                table_name=result.table_name,
                column_count=result.column_count,
                row_count=result.row_count
            )
        finally:
            db.close()
    except ValueError as e:
        _raise_value_error(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/csv/preview", response_model=ImportPreviewResponse)
async def preview_csv_import(
    file: UploadFile = File(...),
    column_types: str | None = Form(default=None, description="JSON object mapping column names to types"),
    current_user: TokenData = Depends(get_current_user)
):
    """Preview what a CSV import will do without committing.

    Returns inferred column types, row count, first 10 rows, and any validation warnings.

    No data is written during preview.
    All roles can preview (viewer, analyst, admin).
    """
    # Parse column_types if provided
    parsed_column_types = None
    if column_types:
        try:
            import json
            parsed_column_types = json.loads(column_types)
            if not isinstance(parsed_column_types, dict):
                raise ValueError("column_types must be a JSON object")
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid column_types JSON: {str(e)}"
            )

    try:
        db = SessionLocal()
        try:
            import_service = CSVImportService(db)

            preview = import_service.preview_csv(
                file=file.file,
                column_types=parsed_column_types
            )

            return ImportPreviewResponse(
                inferred_columns=[
                    InferredColumn(name=col["name"], type=col["type"])
                    for col in preview.inferred_columns
                ],
                row_count=preview.row_count,
                sample_rows=preview.sample_rows,
                validation_warnings=[
                    ImportValidationError(
                        row=err.row,
                        column=err.column,
                        expected=err.expected,
                        value=err.value,
                        message=err.message
                    )
                    for err in preview.validation_warnings
                ]
            )
        finally:
            db.close()
    except ValueError as e:
        _raise_value_error(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{table_id}/import/csv", response_model=ImportReplaceResultResponse | ImportAppendResultResponse)
async def import_csv_to_table(
    table_id: UUID,
    file: UploadFile = File(...),
    mode: str = Query(default="replace", description="Import mode: 'replace' (delete existing) or 'append'"),
    current_user: TokenData = Depends(get_current_user)
):
    """Import CSV data into an existing table.

    Mode options:
    - replace: Delete all existing rows and import new ones (default)
    - append: Add new rows after existing ones

    CSV columns must match existing table columns (by name, order independent).

    Requires analyst or admin role.
    Cannot replace data in tables with approved versions.
    """
    if current_user.role not in WRITE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only analyst or admin can import data"
        )

    if mode not in ("replace", "append"):
        raise HTTPException(
            status_code=400,
            detail="Invalid mode. Use 'replace' or 'append'"
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

            import_service = CSVImportService(db)

            # Check for approved versions if replacing
            if mode == "replace" and import_service.has_approved_versions(table_id):
                raise HTTPException(
                    status_code=403,
                    detail="Cannot replace data in tables with approved versions. "
                           "Create a new version or use append mode."
                )

            if mode == "replace":
                row_count = import_service.replace_table_data(
                    table_id=table_id,
                    file=file.file,
                    tenant_id=current_user.tenant_id
                )
                return ImportReplaceResultResponse(rows_imported=row_count)
            else:  # append
                row_count = import_service.append_table_data(
                    table_id=table_id,
                    file=file.file,
                    tenant_id=current_user.tenant_id
                )
                return ImportAppendResultResponse(rows_added=row_count)

        finally:
            db.close()
    except HTTPException:
        raise
    except ValueError as e:
        _raise_value_error(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
