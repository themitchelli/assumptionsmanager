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

    def submit_for_approval(
        self,
        version_id: UUID,
        user_id: UUID,
        comment: str | None = None
    ) -> dict:
        """Submit a version for approval.

        Transitions status from draft or rejected to submitted.
        Records the submitter and timestamp.
        Creates audit trail entry in approval_history.

        Returns the updated approval record.
        Raises ValueError if current status is not draft or rejected.
        """
        # Get current approval status
        current = self.get_approval_status(version_id)
        if not current:
            # Create approval record if missing (handles migration)
            current = self.create_approval_record(version_id)

        from_status = current["status"]

        # Validate state transition
        if from_status not in ("draft", "rejected"):
            raise ValueError(
                f"Cannot submit version: current status is '{from_status}'. "
                "Only draft or rejected versions can be submitted."
            )

        # Update approval status
        result = self.db.execute(
            text("""
                UPDATE version_approvals
                SET status = 'submitted',
                    submitted_by = :user_id,
                    submitted_at = NOW(),
                    reviewed_by = NULL,
                    reviewed_at = NULL,
                    updated_at = NOW()
                WHERE version_id = :version_id
                RETURNING id, version_id, status, submitted_by, submitted_at,
                          reviewed_by, reviewed_at, created_at, updated_at
            """),
            {"version_id": str(version_id), "user_id": str(user_id)}
        )
        updated_row = result.fetchone()

        # Create approval history entry
        self.db.execute(
            text("""
                INSERT INTO approval_history
                    (version_id, from_status, to_status, changed_by, comment)
                VALUES
                    (:version_id, :from_status, 'submitted', :user_id, :comment)
            """),
            {
                "version_id": str(version_id),
                "from_status": from_status,
                "user_id": str(user_id),
                "comment": comment
            }
        )

        return self._row_to_dict(updated_row)

    def approve(
        self,
        version_id: UUID,
        user_id: UUID,
        comment: str | None = None
    ) -> dict:
        """Approve a submitted version.

        Transitions status from submitted to approved.
        Records the reviewer and timestamp.
        Creates audit trail entry in approval_history.

        Returns the updated approval record.
        Raises ValueError if current status is not submitted.
        """
        # Get current approval status
        current = self.get_approval_status(version_id)
        if not current:
            raise ValueError("Approval record not found for this version")

        from_status = current["status"]

        # Validate state transition
        if from_status != "submitted":
            raise ValueError(
                f"Cannot approve version: current status is '{from_status}'. "
                "Only submitted versions can be approved."
            )

        # Update approval status
        result = self.db.execute(
            text("""
                UPDATE version_approvals
                SET status = 'approved',
                    reviewed_by = :user_id,
                    reviewed_at = NOW(),
                    updated_at = NOW()
                WHERE version_id = :version_id
                RETURNING id, version_id, status, submitted_by, submitted_at,
                          reviewed_by, reviewed_at, created_at, updated_at
            """),
            {"version_id": str(version_id), "user_id": str(user_id)}
        )
        updated_row = result.fetchone()

        # Create approval history entry
        self.db.execute(
            text("""
                INSERT INTO approval_history
                    (version_id, from_status, to_status, changed_by, comment)
                VALUES
                    (:version_id, :from_status, 'approved', :user_id, :comment)
            """),
            {
                "version_id": str(version_id),
                "from_status": from_status,
                "user_id": str(user_id),
                "comment": comment
            }
        )

        return self._row_to_dict(updated_row)

    def reject(
        self,
        version_id: UUID,
        user_id: UUID,
        comment: str
    ) -> dict:
        """Reject a submitted version.

        Transitions status from submitted to rejected.
        Records the reviewer and timestamp.
        Creates audit trail entry in approval_history.

        Comment is required for rejections to help the analyst understand
        what needs to be fixed.

        Returns the updated approval record.
        Raises ValueError if current status is not submitted.
        Raises ValueError if comment is missing or empty.
        """
        # Validate comment is provided
        if not comment or not comment.strip():
            raise ValueError("Comment is required when rejecting a version")

        # Get current approval status
        current = self.get_approval_status(version_id)
        if not current:
            raise ValueError("Approval record not found for this version")

        from_status = current["status"]

        # Validate state transition
        if from_status != "submitted":
            raise ValueError(
                f"Cannot reject version: current status is '{from_status}'. "
                "Only submitted versions can be rejected."
            )

        # Update approval status
        result = self.db.execute(
            text("""
                UPDATE version_approvals
                SET status = 'rejected',
                    reviewed_by = :user_id,
                    reviewed_at = NOW(),
                    updated_at = NOW()
                WHERE version_id = :version_id
                RETURNING id, version_id, status, submitted_by, submitted_at,
                          reviewed_by, reviewed_at, created_at, updated_at
            """),
            {"version_id": str(version_id), "user_id": str(user_id)}
        )
        updated_row = result.fetchone()

        # Create approval history entry
        self.db.execute(
            text("""
                INSERT INTO approval_history
                    (version_id, from_status, to_status, changed_by, comment)
                VALUES
                    (:version_id, :from_status, 'rejected', :user_id, :comment)
            """),
            {
                "version_id": str(version_id),
                "from_status": from_status,
                "user_id": str(user_id),
                "comment": comment.strip()
            }
        )

        return self._row_to_dict(updated_row)

    def get_history(self, version_id: UUID) -> list[dict]:
        """Get the full approval history for a version.

        Returns all state transitions in chronological order (oldest first).
        Includes user names for display.

        Returns empty list for versions with no history entries.
        """
        result = self.db.execute(
            text("""
                SELECT h.id, h.from_status, h.to_status, h.changed_by,
                       u.email as changed_by_name, h.comment, h.created_at
                FROM approval_history h
                LEFT JOIN users u ON u.id = h.changed_by
                WHERE h.version_id = :version_id
                ORDER BY h.created_at ASC
            """),
            {"version_id": str(version_id)}
        )
        rows = result.fetchall()
        return [
            {
                "id": row[0],
                "from_status": row[1],
                "to_status": row[2],
                "changed_by": row[3],
                "changed_by_name": row[4],
                "comment": row[5],
                "created_at": row[6]
            }
            for row in rows
        ]

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
