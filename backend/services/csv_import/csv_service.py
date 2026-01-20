"""CSV Import Service for assumption tables.

Provides CSV import functionality with:
- Type inference (integer, decimal, date, boolean, text)
- RFC 4180 compliant parsing
- UTF-8 encoding with BOM detection
- Streaming parser for memory efficiency
- Atomic transactions (all-or-nothing)
- Clear validation error messages
"""
import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date
from typing import BinaryIO, Iterator
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


# Max errors to return (don't overwhelm with thousands)
MAX_VALIDATION_ERRORS = 20

# Max file size in bytes (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Valid data types
VALID_DATA_TYPES = {"text", "integer", "decimal", "date", "boolean"}


@dataclass
class ValidationError:
    """A single validation error with context."""
    row: int
    column: str
    expected: str
    value: str
    message: str


@dataclass
class ImportPreview:
    """Preview of what an import will do."""
    inferred_columns: list[dict]  # [{"name": "age", "type": "integer"}, ...]
    row_count: int
    sample_rows: list[dict]  # First 10 rows parsed
    validation_warnings: list[ValidationError] = field(default_factory=list)


@dataclass
class ImportResult:
    """Result of a successful import."""
    table_id: UUID
    table_name: str
    column_count: int
    row_count: int


class CSVImportService:
    """Service for importing CSV data into assumption tables."""

    def __init__(self, db: Session):
        self.db = db

    def create_table_from_csv(
        self,
        file: BinaryIO,
        table_name: str,
        tenant_id: UUID,
        created_by: UUID,
        description: str | None = None,
        effective_date: str | None = None,
        column_types: dict[str, str] | None = None
    ) -> ImportResult:
        """Create a new table from CSV file.

        Args:
            file: File-like object containing CSV data
            table_name: Name for the new table
            tenant_id: Tenant UUID
            created_by: User UUID who is creating the table
            description: Optional table description
            effective_date: Optional effective date (YYYY-MM-DD)
            column_types: Optional dict of column_name -> data_type overrides

        Returns:
            ImportResult with table details

        Raises:
            ValueError: If CSV is malformed or validation fails
        """
        # Parse CSV content
        content = self._read_file_content(file)
        rows = list(self._parse_csv(content))

        if not rows:
            raise ValueError("CSV file is empty or has no data rows")

        # First row is headers
        headers = rows[0]
        data_rows = rows[1:]

        if not headers:
            raise ValueError("CSV file has no column headers")

        # Check for duplicate column names
        seen_headers = set()
        for h in headers:
            if h in seen_headers:
                raise ValueError(f"Duplicate column name: '{h}'")
            seen_headers.add(h)

        # Infer or use provided column types
        columns = self._infer_column_types(headers, data_rows, column_types)

        # Validate all data against column types
        errors = self._validate_data(columns, data_rows)
        if errors:
            raise ValueError(self._format_validation_errors(errors))

        # Validate effective_date if provided
        effective_date_value = None
        if effective_date:
            try:
                effective_date_value = date.fromisoformat(effective_date)
            except ValueError:
                raise ValueError("Invalid effective_date format. Use YYYY-MM-DD")

        # Create table
        table_result = self.db.execute(
            text("""
                INSERT INTO assumption_tables (tenant_id, name, description, effective_date, created_by)
                VALUES (:tenant_id, :name, :description, :effective_date, :created_by)
                RETURNING id
            """),
            {
                "tenant_id": str(tenant_id),
                "name": table_name,
                "description": description,
                "effective_date": effective_date_value,
                "created_by": str(created_by)
            }
        )
        table_id = table_result.fetchone()[0]

        # Create columns
        column_ids = {}
        for pos, col in enumerate(columns):
            col_result = self.db.execute(
                text("""
                    INSERT INTO assumption_columns (table_id, name, data_type, position)
                    VALUES (:table_id, :name, :data_type, :position)
                    RETURNING id
                """),
                {
                    "table_id": str(table_id),
                    "name": col["name"],
                    "data_type": col["type"],
                    "position": pos
                }
            )
            column_ids[col["name"]] = col_result.fetchone()[0]

        # Insert rows and cells
        for row_idx, row_data in enumerate(data_rows):
            # Skip empty rows
            if not any(cell.strip() for cell in row_data):
                continue

            row_result = self.db.execute(
                text("""
                    INSERT INTO assumption_rows (table_id, row_index)
                    VALUES (:table_id, :row_index)
                    RETURNING id
                """),
                {"table_id": str(table_id), "row_index": row_idx}
            )
            row_id = row_result.fetchone()[0]

            # Insert cells
            for col_idx, value in enumerate(row_data):
                if col_idx >= len(headers):
                    break
                col_name = headers[col_idx]
                col_type = next(c["type"] for c in columns if c["name"] == col_name)

                # Normalize and store value
                normalized = self._normalize_value(value.strip(), col_type)
                if normalized is not None:
                    self.db.execute(
                        text("""
                            INSERT INTO assumption_cells (row_id, column_id, value)
                            VALUES (:row_id, :column_id, :value)
                        """),
                        {
                            "row_id": str(row_id),
                            "column_id": str(column_ids[col_name]),
                            "value": normalized
                        }
                    )

        self.db.commit()

        return ImportResult(
            table_id=table_id,
            table_name=table_name,
            column_count=len(columns),
            row_count=len([r for r in data_rows if any(cell.strip() for cell in r)])
        )

    def preview_csv(
        self,
        file: BinaryIO,
        column_types: dict[str, str] | None = None
    ) -> ImportPreview:
        """Preview what an import would do without committing.

        Args:
            file: File-like object containing CSV data
            column_types: Optional dict of column_name -> data_type overrides

        Returns:
            ImportPreview with inferred columns, row count, and sample data
        """
        content = self._read_file_content(file)
        rows = list(self._parse_csv(content))

        if not rows:
            raise ValueError("CSV file is empty")

        headers = rows[0]
        data_rows = rows[1:]

        if not headers:
            raise ValueError("CSV file has no column headers")

        # Check for duplicates
        seen = set()
        for h in headers:
            if h in seen:
                raise ValueError(f"Duplicate column name: '{h}'")
            seen.add(h)

        # Infer types
        columns = self._infer_column_types(headers, data_rows, column_types)

        # Validate and collect warnings
        errors = self._validate_data(columns, data_rows)

        # Build sample rows (first 10)
        sample_rows = []
        for row_data in data_rows[:10]:
            row_dict = {}
            for col_idx, value in enumerate(row_data):
                if col_idx < len(headers):
                    row_dict[headers[col_idx]] = value.strip()
            sample_rows.append(row_dict)

        return ImportPreview(
            inferred_columns=columns,
            row_count=len([r for r in data_rows if any(cell.strip() for cell in r)]),
            sample_rows=sample_rows,
            validation_warnings=errors[:MAX_VALIDATION_ERRORS]
        )

    def replace_table_data(
        self,
        table_id: UUID,
        file: BinaryIO,
        tenant_id: UUID
    ) -> int:
        """Replace all data in an existing table from CSV.

        Args:
            table_id: UUID of the table to replace data in
            file: File-like object containing CSV data
            tenant_id: Tenant UUID for verification

        Returns:
            Number of rows imported

        Raises:
            ValueError: If columns don't match or validation fails
        """
        # Verify table exists and belongs to tenant
        table_result = self.db.execute(
            text("""
                SELECT id, name FROM assumption_tables
                WHERE id = :table_id AND tenant_id = :tenant_id
            """),
            {"table_id": str(table_id), "tenant_id": str(tenant_id)}
        )
        table_row = table_result.fetchone()
        if not table_row:
            raise ValueError("Table not found")

        # Get existing column definitions
        col_result = self.db.execute(
            text("""
                SELECT id, name, data_type FROM assumption_columns
                WHERE table_id = :table_id
                ORDER BY position
            """),
            {"table_id": str(table_id)}
        )
        existing_columns = {row[1]: {"id": row[0], "type": row[2]} for row in col_result}

        if not existing_columns:
            raise ValueError("Table has no columns defined")

        # Parse CSV
        content = self._read_file_content(file)
        rows = list(self._parse_csv(content))

        if not rows:
            raise ValueError("CSV file is empty")

        headers = rows[0]
        data_rows = rows[1:]

        # Verify columns match (order independent)
        csv_columns = set(h.strip() for h in headers if h.strip())
        table_columns = set(existing_columns.keys())

        if csv_columns != table_columns:
            missing = table_columns - csv_columns
            extra = csv_columns - table_columns
            msg_parts = []
            if missing:
                msg_parts.append(f"Missing columns: {', '.join(sorted(missing))}")
            if extra:
                msg_parts.append(f"Extra columns: {', '.join(sorted(extra))}")
            raise ValueError(f"Column mismatch. {'. '.join(msg_parts)}")

        # Build columns list for validation
        columns = [{"name": h, "type": existing_columns[h]["type"]} for h in headers]

        # Validate data
        errors = self._validate_data(columns, data_rows)
        if errors:
            raise ValueError(self._format_validation_errors(errors))

        # Delete existing rows (cascades to cells)
        self.db.execute(
            text("DELETE FROM assumption_rows WHERE table_id = :table_id"),
            {"table_id": str(table_id)}
        )

        # Insert new rows
        row_count = 0
        for row_idx, row_data in enumerate(data_rows):
            # Skip empty rows
            if not any(cell.strip() for cell in row_data):
                continue

            row_result = self.db.execute(
                text("""
                    INSERT INTO assumption_rows (table_id, row_index)
                    VALUES (:table_id, :row_index)
                    RETURNING id
                """),
                {"table_id": str(table_id), "row_index": row_idx}
            )
            row_id = row_result.fetchone()[0]
            row_count += 1

            # Insert cells
            for col_idx, value in enumerate(row_data):
                if col_idx >= len(headers):
                    break
                col_name = headers[col_idx]
                col_info = existing_columns[col_name]

                normalized = self._normalize_value(value.strip(), col_info["type"])
                if normalized is not None:
                    self.db.execute(
                        text("""
                            INSERT INTO assumption_cells (row_id, column_id, value)
                            VALUES (:row_id, :column_id, :value)
                        """),
                        {
                            "row_id": str(row_id),
                            "column_id": str(col_info["id"]),
                            "value": normalized
                        }
                    )

        self.db.commit()
        return row_count

    def append_table_data(
        self,
        table_id: UUID,
        file: BinaryIO,
        tenant_id: UUID
    ) -> int:
        """Append rows from CSV to an existing table.

        Args:
            table_id: UUID of the table to append to
            file: File-like object containing CSV data
            tenant_id: Tenant UUID for verification

        Returns:
            Number of rows appended
        """
        # Verify table exists and belongs to tenant
        table_result = self.db.execute(
            text("""
                SELECT id FROM assumption_tables
                WHERE id = :table_id AND tenant_id = :tenant_id
            """),
            {"table_id": str(table_id), "tenant_id": str(tenant_id)}
        )
        if not table_result.fetchone():
            raise ValueError("Table not found")

        # Get existing columns
        col_result = self.db.execute(
            text("""
                SELECT id, name, data_type FROM assumption_columns
                WHERE table_id = :table_id
                ORDER BY position
            """),
            {"table_id": str(table_id)}
        )
        existing_columns = {row[1]: {"id": row[0], "type": row[2]} for row in col_result}

        if not existing_columns:
            raise ValueError("Table has no columns defined")

        # Parse CSV
        content = self._read_file_content(file)
        rows = list(self._parse_csv(content))

        if not rows:
            raise ValueError("CSV file is empty")

        headers = rows[0]
        data_rows = rows[1:]

        # Verify columns match
        csv_columns = set(h.strip() for h in headers if h.strip())
        table_columns = set(existing_columns.keys())

        if csv_columns != table_columns:
            missing = table_columns - csv_columns
            extra = csv_columns - table_columns
            msg_parts = []
            if missing:
                msg_parts.append(f"Missing columns: {', '.join(sorted(missing))}")
            if extra:
                msg_parts.append(f"Extra columns: {', '.join(sorted(extra))}")
            raise ValueError(f"Column mismatch. {'. '.join(msg_parts)}")

        # Build columns list for validation
        columns = [{"name": h, "type": existing_columns[h]["type"]} for h in headers]

        # Validate data
        errors = self._validate_data(columns, data_rows)
        if errors:
            raise ValueError(self._format_validation_errors(errors))

        # Get next row_index
        max_result = self.db.execute(
            text("""
                SELECT COALESCE(MAX(row_index), -1) FROM assumption_rows
                WHERE table_id = :table_id
            """),
            {"table_id": str(table_id)}
        )
        next_index = max_result.fetchone()[0] + 1

        # Insert rows
        row_count = 0
        for row_idx, row_data in enumerate(data_rows):
            # Skip empty rows
            if not any(cell.strip() for cell in row_data):
                continue

            row_result = self.db.execute(
                text("""
                    INSERT INTO assumption_rows (table_id, row_index)
                    VALUES (:table_id, :row_index)
                    RETURNING id
                """),
                {"table_id": str(table_id), "row_index": next_index + row_count}
            )
            row_id = row_result.fetchone()[0]
            row_count += 1

            # Insert cells
            for col_idx, value in enumerate(row_data):
                if col_idx >= len(headers):
                    break
                col_name = headers[col_idx]
                col_info = existing_columns[col_name]

                normalized = self._normalize_value(value.strip(), col_info["type"])
                if normalized is not None:
                    self.db.execute(
                        text("""
                            INSERT INTO assumption_cells (row_id, column_id, value)
                            VALUES (:row_id, :column_id, :value)
                        """),
                        {
                            "row_id": str(row_id),
                            "column_id": str(col_info["id"]),
                            "value": normalized
                        }
                    )

        self.db.commit()
        return row_count

    def has_approved_versions(self, table_id: UUID) -> bool:
        """Check if a table has any approved versions."""
        result = self.db.execute(
            text("""
                SELECT EXISTS(
                    SELECT 1 FROM assumption_versions v
                    JOIN version_approvals va ON va.version_id = v.id
                    WHERE v.table_id = :table_id AND va.status = 'approved'
                )
            """),
            {"table_id": str(table_id)}
        )
        return result.fetchone()[0]

    def _read_file_content(self, file: BinaryIO) -> str:
        """Read file content and decode to string."""
        # Read raw bytes
        raw_content = file.read()

        # Check file size
        if len(raw_content) > MAX_FILE_SIZE:
            raise ValueError(f"File size exceeds maximum of {MAX_FILE_SIZE // (1024*1024)}MB")

        # Try UTF-8 with BOM first
        if raw_content.startswith(b'\xef\xbb\xbf'):
            return raw_content[3:].decode('utf-8')

        # Try UTF-8
        try:
            return raw_content.decode('utf-8')
        except UnicodeDecodeError:
            pass

        # Try Latin-1 (Windows-1252 compatible)
        try:
            return raw_content.decode('latin-1')
        except UnicodeDecodeError:
            pass

        raise ValueError("Unable to decode file. Ensure it is UTF-8 or Latin-1 encoded")

    def _parse_csv(self, content: str) -> Iterator[list[str]]:
        """Parse CSV content, auto-detecting delimiter."""
        # Detect delimiter from first line
        first_line = content.split('\n', 1)[0] if content else ''

        # Count potential delimiters
        comma_count = first_line.count(',')
        semicolon_count = first_line.count(';')
        tab_count = first_line.count('\t')

        if tab_count > comma_count and tab_count > semicolon_count:
            delimiter = '\t'
        elif semicolon_count > comma_count:
            delimiter = ';'
        else:
            delimiter = ','

        # Parse with detected delimiter
        reader = csv.reader(io.StringIO(content), delimiter=delimiter)
        for row in reader:
            # Skip completely empty rows
            if row and any(cell.strip() for cell in row):
                yield [cell.strip() for cell in row]

    def _infer_column_types(
        self,
        headers: list[str],
        data_rows: list[list[str]],
        overrides: dict[str, str] | None = None
    ) -> list[dict]:
        """Infer column types from data, applying any overrides."""
        overrides = overrides or {}

        # Validate override types
        for col_name, dtype in overrides.items():
            if dtype not in VALID_DATA_TYPES:
                raise ValueError(
                    f"Invalid data type '{dtype}' for column '{col_name}'. "
                    f"Valid types: {', '.join(sorted(VALID_DATA_TYPES))}"
                )

        columns = []
        for col_idx, col_name in enumerate(headers):
            if col_name in overrides:
                columns.append({"name": col_name, "type": overrides[col_name]})
            else:
                # Collect non-empty values for this column
                values = []
                for row in data_rows:
                    if col_idx < len(row) and row[col_idx].strip():
                        values.append(row[col_idx].strip())

                inferred_type = self._infer_type_from_values(values)
                columns.append({"name": col_name, "type": inferred_type})

        return columns

    def _infer_type_from_values(self, values: list[str]) -> str:
        """Infer the best data type for a list of values."""
        if not values:
            return "text"  # Default for empty columns

        # Check if all values are booleans
        bool_values = {"true", "false", "yes", "no", "1", "0"}
        if all(v.lower() in bool_values for v in values):
            return "boolean"

        # Check if all values are dates (YYYY-MM-DD)
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        if all(date_pattern.match(v) for v in values):
            # Also verify they're valid dates
            try:
                for v in values:
                    date.fromisoformat(v)
                return "date"
            except ValueError:
                pass

        # Check if all values are integers
        int_pattern = re.compile(r'^-?\d+$')
        if all(int_pattern.match(v) for v in values):
            return "integer"

        # Check if all values are decimals (includes integers)
        decimal_pattern = re.compile(r'^-?\d+\.?\d*$')
        if all(decimal_pattern.match(v) for v in values):
            return "decimal"

        # Default to text
        return "text"

    def _validate_data(
        self,
        columns: list[dict],
        data_rows: list[list[str]]
    ) -> list[ValidationError]:
        """Validate all data against column types."""
        errors = []

        for row_idx, row_data in enumerate(data_rows):
            # Skip empty rows
            if not any(cell.strip() for cell in row_data):
                continue

            for col_idx, col in enumerate(columns):
                if col_idx >= len(row_data):
                    continue

                value = row_data[col_idx].strip()
                if not value:
                    continue  # Empty values are OK

                col_type = col["type"]
                col_name = col["name"]

                error = self._validate_value(value, col_type, col_name, row_idx + 2)  # +2 for 1-indexed + header
                if error:
                    errors.append(error)
                    if len(errors) >= MAX_VALIDATION_ERRORS:
                        return errors

        return errors

    def _validate_value(
        self,
        value: str,
        data_type: str,
        column_name: str,
        row_number: int
    ) -> ValidationError | None:
        """Validate a single value against its expected type."""
        try:
            if data_type == "integer":
                if not re.match(r'^-?\d+$', value):
                    return ValidationError(
                        row=row_number,
                        column=column_name,
                        expected="integer",
                        value=value,
                        message=f"Cannot parse '{value}' as integer. Replace with a whole number or empty cell."
                    )
            elif data_type == "decimal":
                if not re.match(r'^-?\d+\.?\d*$', value):
                    return ValidationError(
                        row=row_number,
                        column=column_name,
                        expected="decimal",
                        value=value,
                        message=f"Cannot parse '{value}' as decimal. Replace with a valid number or empty cell."
                    )
            elif data_type == "date":
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', value):
                    return ValidationError(
                        row=row_number,
                        column=column_name,
                        expected="date",
                        value=value,
                        message=f"Cannot parse '{value}' as date. Use YYYY-MM-DD format or empty cell."
                    )
                # Also validate it's a real date
                date.fromisoformat(value)
            elif data_type == "boolean":
                if value.lower() not in {"true", "false", "yes", "no", "1", "0"}:
                    return ValidationError(
                        row=row_number,
                        column=column_name,
                        expected="boolean",
                        value=value,
                        message=f"Cannot parse '{value}' as boolean. Use true/false, yes/no, 1/0, or empty cell."
                    )
        except ValueError:
            return ValidationError(
                row=row_number,
                column=column_name,
                expected=data_type,
                value=value,
                message=f"Invalid {data_type} value: '{value}'"
            )

        return None

    def _normalize_value(self, value: str, data_type: str) -> str | None:
        """Normalize a value for storage. Returns None for empty values."""
        if not value:
            return None

        if data_type == "boolean":
            return "true" if value.lower() in ("true", "1", "yes") else "false"
        elif data_type == "integer":
            return str(int(value))
        elif data_type == "decimal":
            # Preserve precision - don't convert through float
            return value
        else:
            return value

    def _format_validation_errors(self, errors: list[ValidationError]) -> str:
        """Format validation errors into a user-friendly message."""
        if len(errors) == 1:
            e = errors[0]
            return f"Validation error at row {e.row}, column '{e.column}': {e.message}"

        error_details = []
        for e in errors[:MAX_VALIDATION_ERRORS]:
            error_details.append({
                "row": e.row,
                "column": e.column,
                "expected": e.expected,
                "value": e.value,
                "message": e.message
            })

        if len(errors) > MAX_VALIDATION_ERRORS:
            return f"Found {len(errors)} validation errors (showing first {MAX_VALIDATION_ERRORS}). First error: {errors[0].message}"

        return f"Found {len(errors)} validation errors. First error at row {errors[0].row}, column '{errors[0].column}': {errors[0].message}"
