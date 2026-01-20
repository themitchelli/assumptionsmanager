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

        return {
            "id": version_row[0],
            "version_number": version_row[1],
            "comment": version_row[2],
            "created_by": version_row[3],
            "created_at": version_row[4]
        }

    def get_version(self, version_id: UUID) -> dict | None:
        """Get version metadata by ID."""
        result = self.db.execute(
            text("""
                SELECT v.id, v.table_id, v.version_number, v.comment,
                       v.created_by, v.created_at, u.email as created_by_email
                FROM assumption_versions v
                JOIN users u ON u.id = v.created_by
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
            "created_at": row[5]
        }

    def list_versions(self, table_id: UUID) -> list[dict]:
        """List all versions for a table, newest first."""
        result = self.db.execute(
            text("""
                SELECT v.id, v.version_number, v.comment,
                       v.created_by, v.created_at, u.email as created_by_name
                FROM assumption_versions v
                JOIN users u ON u.id = v.created_by
                WHERE v.table_id = :table_id
                ORDER BY v.version_number DESC
            """),
            {"table_id": str(table_id)}
        )

        return [
            {
                "id": row[0],
                "version_number": row[1],
                "comment": row[2],
                "created_by": row[3],
                "created_by_name": row[5],
                "created_at": row[4]
            }
            for row in result
        ]

    def get_version_data(self, version_id: UUID) -> list[dict]:
        """Get all cell data for a version snapshot.

        Returns list of cells with row_index, column_name, value.
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

        return [
            {
                "row_index": row[0],
                "column_name": row[1],
                "value": row[2]
            }
            for row in result
        ]

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
