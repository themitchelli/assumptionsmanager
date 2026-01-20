from uuid import UUID
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session


class ApprovalService:
    """Service for managing version approval workflow.

    Provides state machine for approval transitions:
    - draft -> submitted (analyst/admin)
    - submitted -> approved (admin only)
    - submitted -> rejected (admin only)
    - rejected -> submitted (analyst/admin - resubmit)
    - approved is terminal (no further transitions)
    """

    def __init__(self, db: Session):
        self.db = db

    def create_approval_record(self, version_id: UUID) -> dict:
        """Create initial approval record for a new version.

        All new versions start in 'draft' status.
        """
        result = self.db.execute(
            text("""
                INSERT INTO version_approvals (version_id, status)
                VALUES (:version_id, 'draft')
                RETURNING id, version_id, status, submitted_by, submitted_at,
                          reviewed_by, reviewed_at, created_at, updated_at
            """),
            {"version_id": str(version_id)}
        )
        row = result.fetchone()
        return self._row_to_dict(row)

    def get_approval_status(self, version_id: UUID) -> dict | None:
        """Get approval status for a version."""
        result = self.db.execute(
            text("""
                SELECT id, version_id, status, submitted_by, submitted_at,
                       reviewed_by, reviewed_at, created_at, updated_at
                FROM version_approvals
                WHERE version_id = :version_id
            """),
            {"version_id": str(version_id)}
        )
        row = result.fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def ensure_approval_record_exists(self, version_id: UUID) -> dict:
        """Ensure an approval record exists for a version.

        Creates one with 'draft' status if it doesn't exist.
        This handles migration of existing versions.
        """
        existing = self.get_approval_status(version_id)
        if existing:
            return existing
        return self.create_approval_record(version_id)

    def _row_to_dict(self, row) -> dict:
        """Convert a database row to a dictionary."""
        return {
            "id": row[0],
            "version_id": row[1],
            "status": row[2],
            "submitted_by": row[3],
            "submitted_at": row[4],
            "reviewed_by": row[5],
            "reviewed_at": row[6],
            "created_at": row[7],
            "updated_at": row[8]
        }
