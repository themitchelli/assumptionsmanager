from uuid import UUID
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session


class VersioningService:
    """Service for managing version snapshots of entities.

    Currently supports assumption tables. Designed with entity-agnostic
    interface for future extraction to standalone service.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_snapshot(
        self,
        entity_type: str,
        entity_id: UUID,
        user_id: UUID,
        comment: str,
        context: dict | None = None
    ) -> dict:
        """Create a version snapshot of an entity.

        Args:
            entity_type: Type of entity (currently only 'assumption_table')
            entity_id: UUID of the entity to snapshot
            user_id: UUID of user creating the snapshot
            comment: Description of this version
            context: Optional JSON context data for future extensibility

        Returns:
            Version metadata dict with id, version_number, comment, created_by, created_at

        Raises:
            ValueError: If entity_type is not supported
        """
        if entity_type != "assumption_table":
            raise ValueError(f"Unsupported entity_type: {entity_type}")

        return self._create_table_snapshot(entity_id, user_id, comment, context or {})

    def _create_table_snapshot(
        self,
        table_id: UUID,
        user_id: UUID,
        comment: str,
        context: dict
    ) -> dict:
        """Create a version snapshot of an assumption table.

        Copies all current rows and cells into version_cells table.
        Auto-increments version_number for this table.
        """
        # Get next version number for this table
        result = self.db.execute(
            text("""
                SELECT COALESCE(MAX(version_number), 0) + 1
                FROM assumption_versions
                WHERE table_id = :table_id
            """),
            {"table_id": str(table_id)}
        )
        version_number = result.scalar()

        # Create version record
        version_result = self.db.execute(
            text("""
                INSERT INTO assumption_versions (table_id, version_number, comment, created_by, context)
                VALUES (:table_id, :version_number, :comment, :created_by, :context)
                RETURNING id, version_number, comment, created_by, created_at
            """),
            {
                "table_id": str(table_id),
                "version_number": version_number,
                "comment": comment,
                "created_by": str(user_id),
                "context": str(context).replace("'", '"') if context else "{}"
            }
        )
        version_row = version_result.fetchone()
        version_id = version_row[0]

        # Copy all current cells into version_cells
        # We denormalize column_name for snapshot self-containment
        self.db.execute(
            text("""
                INSERT INTO assumption_version_cells (version_id, column_id, column_name, row_index, value)
                SELECT
                    :version_id,
                    ac.column_id,
                    acol.name,
                    ar.row_index,
                    ac.value
                FROM assumption_cells ac
                JOIN assumption_rows ar ON ar.id = ac.row_id
                JOIN assumption_columns acol ON acol.id = ac.column_id
                WHERE ar.table_id = :table_id
            """),
            {"version_id": str(version_id), "table_id": str(table_id)}
        )

        # Create initial approval record (draft status)
        self.db.execute(
            text("""
                INSERT INTO version_approvals (version_id, status)
                VALUES (:version_id, 'draft')
            """),
            {"version_id": str(version_id)}
        )

        return {
            "id": version_row[0],
            "version_number": version_row[1],
            "comment": version_row[2],
            "created_by": version_row[3],
            "created_at": version_row[4]
        }

    def get_version(self, version_id: UUID) -> dict | None:
        """Get version metadata by ID, including approval status."""
        result = self.db.execute(
            text("""
                SELECT v.id, v.table_id, v.version_number, v.comment,
                       v.created_by, v.created_at, u.email as created_by_email,
                       COALESCE(va.status, 'draft') as approval_status,
                       va.submitted_by, va.submitted_at,
                       va.reviewed_by, va.reviewed_at
                FROM assumption_versions v
                JOIN users u ON u.id = v.created_by
                LEFT JOIN version_approvals va ON va.version_id = v.id
                WHERE v.id = :version_id
            """),
            {"version_id": str(version_id)}
        )
        row = result.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "table_id": row[1],
            "version_number": row[2],
            "comment": row[3],
            "created_by": row[4],
            "created_by_email": row[6],
            "created_at": row[5],
            "approval_status": row[7],
            "submitted_by": row[8],
            "submitted_at": row[9],
            "reviewed_by": row[10],
            "reviewed_at": row[11]
        }

    def list_versions(self, table_id: UUID, status_filter: list[str] | None = None) -> list[dict]:
        """List all versions for a table, newest first.

        Args:
            table_id: UUID of the table
            status_filter: Optional list of approval statuses to filter by
        """
        query = """
            SELECT v.id, v.version_number, v.comment,
                   v.created_by, v.created_at, u.email as created_by_name,
                   COALESCE(va.status, 'draft') as approval_status
            FROM assumption_versions v
            JOIN users u ON u.id = v.created_by
            LEFT JOIN version_approvals va ON va.version_id = v.id
            WHERE v.table_id = :table_id
        """
        params: dict = {"table_id": str(table_id)}

        if status_filter:
            # Use IN clause with dynamically generated placeholders
            placeholders = ", ".join([f":status_{i}" for i in range(len(status_filter))])
            query += f" AND COALESCE(va.status, 'draft') IN ({placeholders})"
            for i, status in enumerate(status_filter):
                params[f"status_{i}"] = status

        query += " ORDER BY v.version_number DESC"

        result = self.db.execute(text(query), params)

        return [
            {
                "id": row[0],
                "version_number": row[1],
                "comment": row[2],
                "created_by": row[3],
                "created_by_name": row[5],
                "created_at": row[4],
                "approval_status": row[6]
            }
            for row in result
        ]

    def get_version_data(self, version_id: UUID, table_id: UUID | None = None) -> list[dict]:
        """Get all cell data for a version snapshot.

        Returns list of cells with row_index, column_name, value (typed).
        If table_id is provided, values are cast to their column types.
        """
        result = self.db.execute(
            text("""
                SELECT row_index, column_name, value
                FROM assumption_version_cells
                WHERE version_id = :version_id
                ORDER BY row_index, column_name
            """),
            {"version_id": str(version_id)}
        )

        cells = [
            {
                "row_index": row[0],
                "column_name": row[1],
                "value": row[2]
            }
            for row in result
        ]

        # If table_id provided, cast values to their column types
        if table_id:
            col_result = self.db.execute(
                text("""
                    SELECT name, data_type FROM assumption_columns
                    WHERE table_id = :table_id
                """),
                {"table_id": str(table_id)}
            )
            column_types = {row[0]: row[1] for row in col_result}

            for cell in cells:
                col_type = column_types.get(cell["column_name"], "text")
                cell["value"] = self._cast_value(cell["value"], col_type)

        return cells

    def _cast_value(self, value: str | None, data_type: str):
        """Cast string value to appropriate Python type."""
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

    def count_versions(self, table_id: UUID) -> int:
        """Count versions for a table."""
        result = self.db.execute(
            text("""
                SELECT COUNT(*) FROM assumption_versions
                WHERE table_id = :table_id
            """),
            {"table_id": str(table_id)}
        )
        return result.scalar()

    def delete_version(self, version_id: UUID) -> bool:
        """Delete a version and its cells. Returns True if deleted."""
        result = self.db.execute(
            text("DELETE FROM assumption_versions WHERE id = :version_id"),
            {"version_id": str(version_id)}
        )
        return result.rowcount > 0

    def restore_version(self, table_id: UUID, version_id: UUID) -> None:
        """Restore table data from a version snapshot.

        Deletes current rows/cells and replaces with version data.
        """
        # Delete current rows (cascades to cells)
        self.db.execute(
            text("DELETE FROM assumption_rows WHERE table_id = :table_id"),
            {"table_id": str(table_id)}
        )

        # Get distinct row indices from version
        row_indices_result = self.db.execute(
            text("""
                SELECT DISTINCT row_index FROM assumption_version_cells
                WHERE version_id = :version_id
                ORDER BY row_index
            """),
            {"version_id": str(version_id)}
        )

        # Create rows and map indices to new row IDs
        row_id_map = {}
        for (row_index,) in row_indices_result:
            result = self.db.execute(
                text("""
                    INSERT INTO assumption_rows (table_id, row_index)
                    VALUES (:table_id, :row_index)
                    RETURNING id
                """),
                {"table_id": str(table_id), "row_index": row_index}
            )
            row_id_map[row_index] = result.scalar()

        # Get column ID mapping (column_name -> current column_id)
        col_result = self.db.execute(
            text("""
                SELECT id, name FROM assumption_columns
                WHERE table_id = :table_id
            """),
            {"table_id": str(table_id)}
        )
        column_map = {row[1]: row[0] for row in col_result}

        # Copy version cells to current cells
        version_cells = self.db.execute(
            text("""
                SELECT row_index, column_name, value
                FROM assumption_version_cells
                WHERE version_id = :version_id
            """),
            {"version_id": str(version_id)}
        )

        for row_index, column_name, value in version_cells:
            if column_name in column_map and row_index in row_id_map:
                self.db.execute(
                    text("""
                        INSERT INTO assumption_cells (row_id, column_id, value)
                        VALUES (:row_id, :column_id, :value)
                    """),
                    {
                        "row_id": str(row_id_map[row_index]),
                        "column_id": str(column_map[column_name]),
                        "value": value
                    }
                )

    def compare_versions(self, version1_id: UUID, version2_id: UUID) -> dict:
        """Compare two versions and return the differences.

        Returns a dict with:
        - added_rows: list of row_index values in v2 but not v1
        - deleted_rows: list of row_index values in v1 but not v2
        - modified_cells: list of {row_index, column_name, old_value, new_value}
        """
        # Get v1 data
        v1_cells = self._get_version_cells_map(version1_id)
        # Get v2 data
        v2_cells = self._get_version_cells_map(version2_id)

        # Get all unique row indices
        v1_rows = set(v1_cells.keys())
        v2_rows = set(v2_cells.keys())

        # Added rows: in v2 but not v1
        added_rows = sorted(list(v2_rows - v1_rows))

        # Deleted rows: in v1 but not v2
        deleted_rows = sorted(list(v1_rows - v2_rows))

        # Modified cells: same row exists in both, compare cell values
        modified_cells = []
        common_rows = v1_rows & v2_rows

        for row_idx in sorted(common_rows):
            v1_row = v1_cells[row_idx]
            v2_row = v2_cells[row_idx]

            # Get all columns in both versions of this row
            all_columns = set(v1_row.keys()) | set(v2_row.keys())

            for col_name in sorted(all_columns):
                old_val = v1_row.get(col_name)
                new_val = v2_row.get(col_name)

                if old_val != new_val:
                    modified_cells.append({
                        "row_index": row_idx,
                        "column_name": col_name,
                        "old_value": old_val,
                        "new_value": new_val
                    })

        return {
            "added_rows": added_rows,
            "deleted_rows": deleted_rows,
            "modified_cells": modified_cells
        }

    def _get_version_cells_map(self, version_id: UUID) -> dict[int, dict[str, str | None]]:
        """Get version cells as a map of row_index -> {column_name: value}."""
        result = self.db.execute(
            text("""
                SELECT row_index, column_name, value
                FROM assumption_version_cells
                WHERE version_id = :version_id
            """),
            {"version_id": str(version_id)}
        )

        cells_map: dict[int, dict[str, str | None]] = {}
        for row_index, column_name, value in result:
            if row_index not in cells_map:
                cells_map[row_index] = {}
            cells_map[row_index][column_name] = value

        return cells_map

    def get_formatted_diff(
        self,
        version1_id: UUID,
        version2_id: UUID,
        columns_filter: list[str] | None = None,
        row_start: int | None = None,
        row_end: int | None = None
    ) -> dict:
        """Get a formatted diff between two versions with full context.

        Returns structured diff with:
        - version_a/version_b metadata
        - summary stats
        - column_summary per column
        - changes: list of row changes with full cell context

        Args:
            version1_id: First version (v1/older)
            version2_id: Second version (v2/newer)
            columns_filter: Optional list of column names to include
            row_start: Optional start row index (inclusive)
            row_end: Optional end row index (inclusive)
        """
        # Get version metadata
        v1_meta = self.get_version(version1_id)
        v2_meta = self.get_version(version2_id)

        # Get cell data for both versions
        v1_cells = self._get_version_cells_map(version1_id)
        v2_cells = self._get_version_cells_map(version2_id)

        # Apply row range filter if specified
        if row_start is not None or row_end is not None:
            v1_cells = self._filter_rows(v1_cells, row_start, row_end)
            v2_cells = self._filter_rows(v2_cells, row_start, row_end)

        # Apply column filter if specified
        if columns_filter:
            v1_cells = self._filter_columns(v1_cells, columns_filter)
            v2_cells = self._filter_columns(v2_cells, columns_filter)

        # Get all row indices
        v1_rows = set(v1_cells.keys())
        v2_rows = set(v2_cells.keys())

        added_rows = sorted(v2_rows - v1_rows)
        deleted_rows = sorted(v1_rows - v2_rows)
        common_rows = v1_rows & v2_rows

        # Track column-level changes
        column_changes: dict[str, dict] = {}

        # Get all unique column names
        all_columns: set[str] = set()
        for row_data in v1_cells.values():
            all_columns.update(row_data.keys())
        for row_data in v2_cells.values():
            all_columns.update(row_data.keys())

        for col in all_columns:
            column_changes[col] = {
                "change_count": 0,
                "has_additions": False,
                "has_removals": False,
                "has_modifications": False
            }

        # Build changes list
        changes = []

        # Process added rows
        for row_idx in added_rows:
            row_cells = v2_cells[row_idx]
            cells = []
            for col_name, value in sorted(row_cells.items()):
                cells.append({
                    "column_name": col_name,
                    "value": value,
                    "status": "added"
                })
                column_changes[col_name]["change_count"] += 1
                column_changes[col_name]["has_additions"] = True

            changes.append({
                "type": "row_added",
                "row_index": row_idx,
                "cells": cells
            })

        # Process deleted rows
        for row_idx in deleted_rows:
            row_cells = v1_cells[row_idx]
            cells = []
            for col_name, value in sorted(row_cells.items()):
                cells.append({
                    "column_name": col_name,
                    "value": value,
                    "status": "removed"
                })
                column_changes[col_name]["change_count"] += 1
                column_changes[col_name]["has_removals"] = True

            changes.append({
                "type": "row_removed",
                "row_index": row_idx,
                "cells": cells
            })

        # Process modified rows - include all cells with status markers
        cells_modified_count = 0
        for row_idx in sorted(common_rows):
            v1_row = v1_cells[row_idx]
            v2_row = v2_cells[row_idx]

            # Get all columns in this row
            all_row_cols = set(v1_row.keys()) | set(v2_row.keys())

            row_has_changes = False
            cells = []

            for col_name in sorted(all_row_cols):
                old_val = v1_row.get(col_name)
                new_val = v2_row.get(col_name)

                if col_name not in v1_row:
                    # Cell added in this row
                    cells.append({
                        "column_name": col_name,
                        "new_value": new_val,
                        "status": "added"
                    })
                    row_has_changes = True
                    cells_modified_count += 1
                    column_changes[col_name]["change_count"] += 1
                    column_changes[col_name]["has_additions"] = True
                elif col_name not in v2_row:
                    # Cell removed in this row
                    cells.append({
                        "column_name": col_name,
                        "old_value": old_val,
                        "status": "removed"
                    })
                    row_has_changes = True
                    cells_modified_count += 1
                    column_changes[col_name]["change_count"] += 1
                    column_changes[col_name]["has_removals"] = True
                elif old_val != new_val:
                    # Cell modified
                    cells.append({
                        "column_name": col_name,
                        "old_value": old_val,
                        "new_value": new_val,
                        "status": "modified"
                    })
                    row_has_changes = True
                    cells_modified_count += 1
                    column_changes[col_name]["change_count"] += 1
                    column_changes[col_name]["has_modifications"] = True
                else:
                    # Cell unchanged - include for context
                    cells.append({
                        "column_name": col_name,
                        "value": new_val,
                        "status": "unchanged"
                    })

            if row_has_changes:
                changes.append({
                    "type": "row_modified",
                    "row_index": row_idx,
                    "cells": cells
                })

        # Count cells in added rows for total
        cells_in_added_rows = sum(len(v2_cells[idx]) for idx in added_rows)
        cells_in_removed_rows = sum(len(v1_cells[idx]) for idx in deleted_rows)

        # Build summary
        summary = {
            "total_changes": cells_in_added_rows + cells_in_removed_rows + cells_modified_count,
            "rows_added": len(added_rows),
            "rows_removed": len(deleted_rows),
            "cells_modified": cells_modified_count
        }

        # Build column summary (only include columns with changes or explicitly filtered)
        column_summary = []
        for col_name in sorted(all_columns):
            col_data = column_changes[col_name]
            if col_data["change_count"] > 0 or columns_filter:
                column_summary.append({
                    "column_name": col_name,
                    "change_count": col_data["change_count"],
                    "has_additions": col_data["has_additions"],
                    "has_removals": col_data["has_removals"],
                    "has_modifications": col_data["has_modifications"]
                })

        return {
            "table_id": v1_meta["table_id"],
            "version_a": {
                "id": v1_meta["id"],
                "version_number": v1_meta["version_number"],
                "created_by": v1_meta["created_by"],
                "created_by_name": v1_meta.get("created_by_email"),
                "created_at": v1_meta["created_at"],
                "comment": v1_meta["comment"]
            },
            "version_b": {
                "id": v2_meta["id"],
                "version_number": v2_meta["version_number"],
                "created_by": v2_meta["created_by"],
                "created_by_name": v2_meta.get("created_by_email"),
                "created_at": v2_meta["created_at"],
                "comment": v2_meta["comment"]
            },
            "summary": summary,
            "column_summary": column_summary,
            "changes": changes
        }

    def _filter_rows(
        self,
        cells_map: dict[int, dict[str, str | None]],
        row_start: int | None,
        row_end: int | None
    ) -> dict[int, dict[str, str | None]]:
        """Filter cells map to only include rows in range (inclusive)."""
        filtered = {}
        for row_idx, row_data in cells_map.items():
            if row_start is not None and row_idx < row_start:
                continue
            if row_end is not None and row_idx > row_end:
                continue
            filtered[row_idx] = row_data
        return filtered

    def _filter_columns(
        self,
        cells_map: dict[int, dict[str, str | None]],
        columns: list[str]
    ) -> dict[int, dict[str, str | None]]:
        """Filter cells map to only include specified columns."""
        columns_set = set(columns)
        filtered = {}
        for row_idx, row_data in cells_map.items():
            filtered_row = {k: v for k, v in row_data.items() if k in columns_set}
            if filtered_row:  # Only include rows that have at least one filtered column
                filtered[row_idx] = filtered_row
        return filtered

    def get_all_column_names(self, table_id: UUID) -> set[str]:
        """Get all column names for a table."""
        result = self.db.execute(
            text("SELECT name FROM assumption_columns WHERE table_id = :table_id"),
            {"table_id": str(table_id)}
        )
        return {row[0] for row in result}
