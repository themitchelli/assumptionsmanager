"""CSV Export Service for assumption tables.

Provides RFC 4180 compliant CSV export with:
- UTF-8 encoding with BOM for Excel Windows compatibility
- CRLF line endings
- Proper quoting and escaping of special characters
- Streaming support for large tables
- Optional metadata headers
"""
import csv
import io
from datetime import datetime
from typing import Generator, Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


# UTF-8 BOM for Excel Windows compatibility
UTF8_BOM = "\ufeff"


class CSVExportService:
    """Service for exporting assumption table data to CSV format."""

    def __init__(self, db: Session):
        self.db = db

    def export_table(
        self,
        table_id: UUID,
        include_metadata: bool = False
    ) -> Generator[str, None, None]:
        """Export current table state to CSV with streaming.

        Args:
            table_id: UUID of the table to export
            include_metadata: If True, include metadata header rows prefixed with '#'

        Yields:
            CSV content chunks for streaming response
        """
        # Get table metadata
        table_meta = self._get_table_metadata(table_id)
        if not table_meta:
            raise ValueError(f"Table {table_id} not found")

        # Get column definitions in position order
        columns = self._get_columns(table_id)
        if not columns:
            raise ValueError(f"Table {table_id} has no columns")

        # Yield BOM for Excel compatibility
        yield UTF8_BOM

        # Yield metadata if requested
        if include_metadata:
            yield from self._generate_metadata_rows(table_meta)

        # Yield header row
        yield self._format_csv_row([col["name"] for col in columns])

        # Stream rows
        yield from self._stream_rows(table_id, columns)

    def export_version(
        self,
        table_id: UUID,
        version_id: UUID,
        include_metadata: bool = False
    ) -> Generator[str, None, None]:
        """Export a specific version snapshot to CSV with streaming.

        Args:
            table_id: UUID of the table
            version_id: UUID of the version to export
            include_metadata: If True, include metadata header rows

        Yields:
            CSV content chunks for streaming response
        """
        # Get table metadata
        table_meta = self._get_table_metadata(table_id)
        if not table_meta:
            raise ValueError(f"Table {table_id} not found")

        # Get version metadata
        version_meta = self._get_version_metadata(version_id, table_id)
        if not version_meta:
            raise ValueError(f"Version {version_id} not found")

        # Get column definitions
        columns = self._get_columns(table_id)
        if not columns:
            raise ValueError(f"Table {table_id} has no columns")

        # Yield BOM
        yield UTF8_BOM

        # Yield metadata if requested
        if include_metadata:
            yield from self._generate_metadata_rows(table_meta, version_meta)

        # Yield header row
        yield self._format_csv_row([col["name"] for col in columns])

        # Stream version rows
        yield from self._stream_version_rows(version_id, columns)

    def get_latest_approved_version(self, table_id: UUID) -> dict | None:
        """Get the latest approved version for a table.

        Returns:
            Version metadata dict or None if no approved version exists
        """
        result = self.db.execute(
            text("""
                SELECT v.id, v.version_number, v.comment, v.created_by,
                       v.created_at, u.email as created_by_name,
                       va.status, va.submitted_by, va.submitted_at,
                       va.reviewed_by, va.reviewed_at
                FROM assumption_versions v
                JOIN users u ON u.id = v.created_by
                JOIN version_approvals va ON va.version_id = v.id
                WHERE v.table_id = :table_id AND va.status = 'approved'
                ORDER BY v.version_number DESC
                LIMIT 1
            """),
            {"table_id": str(table_id)}
        )
        row = result.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "version_number": row[1],
            "comment": row[2],
            "created_by": row[3],
            "created_at": row[4],
            "created_by_name": row[5],
            "approval_status": row[6],
            "submitted_by": row[7],
            "submitted_at": row[8],
            "reviewed_by": row[9],
            "reviewed_at": row[10]
        }

    def _get_table_metadata(self, table_id: UUID) -> dict | None:
        """Get table metadata for export headers."""
        result = self.db.execute(
            text("""
                SELECT id, name, description, effective_date, created_by, created_at
                FROM assumption_tables
                WHERE id = :table_id
            """),
            {"table_id": str(table_id)}
        )
        row = result.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "effective_date": str(row[3]) if row[3] else None,
            "created_by": row[4],
            "created_at": row[5]
        }

    def _get_version_metadata(self, version_id: UUID, table_id: UUID) -> dict | None:
        """Get version metadata for export headers."""
        result = self.db.execute(
            text("""
                SELECT v.id, v.version_number, v.comment, v.created_by,
                       v.created_at, u.email as created_by_name,
                       COALESCE(va.status, 'draft') as approval_status
                FROM assumption_versions v
                JOIN users u ON u.id = v.created_by
                LEFT JOIN version_approvals va ON va.version_id = v.id
                WHERE v.id = :version_id AND v.table_id = :table_id
            """),
            {"version_id": str(version_id), "table_id": str(table_id)}
        )
        row = result.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "version_number": row[1],
            "comment": row[2],
            "created_by": row[3],
            "created_at": row[4],
            "created_by_name": row[5],
            "approval_status": row[6]
        }

    def _get_columns(self, table_id: UUID) -> list[dict]:
        """Get column definitions in position order."""
        result = self.db.execute(
            text("""
                SELECT id, name, data_type, position
                FROM assumption_columns
                WHERE table_id = :table_id
                ORDER BY position
            """),
            {"table_id": str(table_id)}
        )
        return [
            {"id": row[0], "name": row[1], "data_type": row[2], "position": row[3]}
            for row in result
        ]

    def _generate_metadata_rows(
        self,
        table_meta: dict,
        version_meta: dict | None = None
    ) -> Generator[str, None, None]:
        """Generate metadata comment rows for CSV header."""
        export_timestamp = datetime.utcnow().isoformat() + "Z"

        yield self._format_comment_row(f"Table: {table_meta['name']}")
        if table_meta.get("description"):
            yield self._format_comment_row(f"Description: {table_meta['description']}")
        if table_meta.get("effective_date"):
            yield self._format_comment_row(f"Effective Date: {table_meta['effective_date']}")
        yield self._format_comment_row(f"Exported: {export_timestamp}")

        if version_meta:
            yield self._format_comment_row(f"Version: {version_meta['version_number']}")
            yield self._format_comment_row(f"Created By: {version_meta['created_by_name']}")
            yield self._format_comment_row(f"Created At: {version_meta['created_at'].isoformat() if hasattr(version_meta['created_at'], 'isoformat') else version_meta['created_at']}")
            yield self._format_comment_row(f"Approval Status: {version_meta['approval_status']}")

    def _format_comment_row(self, content: str) -> str:
        """Format a metadata comment row with # prefix and CRLF ending."""
        return f"# {content}\r\n"

    def _format_csv_row(self, values: list[Any]) -> str:
        """Format a row as RFC 4180 compliant CSV with CRLF ending.

        - Fields containing commas, quotes, or newlines are quoted
        - Quotes within fields are escaped by doubling
        - Uses CRLF line endings for Windows compatibility
        """
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\r\n")
        writer.writerow(values)
        return output.getvalue()

    def _stream_rows(
        self,
        table_id: UUID,
        columns: list[dict]
    ) -> Generator[str, None, None]:
        """Stream current table rows as CSV.

        Uses JOIN to fetch rows with cells in batches for memory efficiency.
        """
        column_ids = [str(col["id"]) for col in columns]
        column_types = {str(col["id"]): col["data_type"] for col in columns}
        column_names_by_id = {str(col["id"]): col["name"] for col in columns}

        # Fetch rows with cells using JOIN for efficiency
        batch_size = 1000
        offset = 0

        while True:
            # Fetch rows with their cells in one query using JOIN
            result = self.db.execute(
                text("""
                    SELECT r.id, r.row_index, c.column_id, c.value
                    FROM assumption_rows r
                    LEFT JOIN assumption_cells c ON c.row_id = r.id
                    WHERE r.table_id = :table_id
                    ORDER BY r.row_index, c.column_id
                    LIMIT :limit OFFSET :offset
                """),
                {"table_id": str(table_id), "limit": batch_size * len(columns) + batch_size, "offset": offset}
            )
            all_rows = list(result)

            if not all_rows:
                break

            # Group cells by row
            rows_dict: dict[str, dict] = {}
            for row in all_rows:
                row_id = str(row[0])
                if row_id not in rows_dict:
                    rows_dict[row_id] = {
                        "id": row[0],
                        "row_index": row[1],
                        "cells": {}
                    }
                if row[2]:  # column_id exists (has cell data)
                    col_id = str(row[2])
                    rows_dict[row_id]["cells"][col_id] = row[3]

            # Yield rows in order
            sorted_rows = sorted(rows_dict.values(), key=lambda x: x["row_index"])
            for row_data in sorted_rows:
                row_cells = row_data["cells"]

                # Build row values in column order
                values = []
                for col_id in column_ids:
                    raw_value = row_cells.get(col_id)
                    formatted = self._format_cell_value(raw_value, column_types[col_id])
                    values.append(formatted)

                yield self._format_csv_row(values)

            # If we got fewer rows than expected, we're done
            if len(sorted_rows) < batch_size:
                break

            offset += len(all_rows)

    def _stream_version_rows(
        self,
        version_id: UUID,
        columns: list[dict]
    ) -> Generator[str, None, None]:
        """Stream version snapshot rows as CSV.

        Fetches cells in batches using OFFSET/LIMIT for memory efficiency.
        """
        column_names = [col["name"] for col in columns]
        column_types = {col["name"]: col["data_type"] for col in columns}

        # Fetch version cells in batches
        batch_size = 1000
        offset = 0

        # Get all cells ordered by row_index and process in batches
        while True:
            cells_result = self.db.execute(
                text("""
                    SELECT row_index, column_name, value
                    FROM assumption_version_cells
                    WHERE version_id = :version_id
                    ORDER BY row_index, column_name
                    LIMIT :limit OFFSET :offset
                """),
                {"version_id": str(version_id), "limit": batch_size * len(columns) + batch_size, "offset": offset}
            )
            all_cells = list(cells_result)

            if not all_cells:
                break

            # Build cell lookup: row_index -> column_name -> value
            cells_map: dict[int, dict[str, str | None]] = {}
            for cell_row in all_cells:
                row_idx = cell_row[0]
                col_name = cell_row[1]
                if row_idx not in cells_map:
                    cells_map[row_idx] = {}
                cells_map[row_idx][col_name] = cell_row[2]

            # Yield each row in order
            for row_idx in sorted(cells_map.keys()):
                row_cells = cells_map[row_idx]

                # Build row values in column order
                values = []
                for col_name in column_names:
                    raw_value = row_cells.get(col_name)
                    col_type = column_types.get(col_name, "text")
                    formatted = self._format_cell_value(raw_value, col_type)
                    values.append(formatted)

                yield self._format_csv_row(values)

            # If we got fewer cells than a full batch, we're done
            if len(all_cells) < batch_size * len(columns):
                break

            offset += len(all_cells)

    def _format_cell_value(self, value: str | None, data_type: str) -> str:
        """Format a cell value for CSV export.

        - NULL/empty cells -> empty string
        - Decimals maintain precision (no rounding)
        - Dates in ISO format (YYYY-MM-DD)
        - Booleans as 'true'/'false' strings
        """
        if value is None:
            return ""

        if data_type == "boolean":
            # Normalize boolean strings
            return "true" if value.lower() in ("true", "1", "yes") else "false"
        elif data_type == "date":
            # Already stored in ISO format, return as-is
            return value
        elif data_type == "decimal":
            # Return raw string to preserve precision
            return value
        elif data_type == "integer":
            # Return as-is
            return value
        else:
            # Text - return as-is
            return value
