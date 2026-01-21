from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    tenant_id: UUID


class UserResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    role: str
    created_at: datetime
    tenant_name: str | None = None

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    user_id: UUID
    tenant_id: UUID
    role: str


class TenantCreate(BaseModel):
    name: str


class TenantCreateWithAdmin(BaseModel):
    """Create tenant with initial admin user"""
    name: str
    admin_email: EmailStr
    admin_name: str


class TenantCreateResponse(BaseModel):
    """Response after creating tenant with admin"""
    id: UUID
    name: str
    created_at: datetime
    admin_id: UUID
    admin_email: str

    class Config:
        from_attributes = True


class TenantUpdate(BaseModel):
    """Partial update for tenant settings"""
    name: str | None = None
    status: str | None = None  # "active" or "inactive" - only super_admin can change


class TenantResponse(BaseModel):
    id: UUID
    name: str
    status: str = "active"  # "active" or "inactive"
    created_at: datetime

    class Config:
        from_attributes = True


class TenantListItemResponse(BaseModel):
    """Extended tenant info for admin list view"""
    id: UUID
    name: str
    user_count: int
    status: str = "active"  # "active" or "inactive"
    created_at: datetime

    class Config:
        from_attributes = True


class TenantListResponse(BaseModel):
    """Response containing list of tenants with stats"""
    tenants: list[TenantListItemResponse]


class PlatformStatsResponse(BaseModel):
    """Platform-wide statistics for super_admin dashboard"""
    total_tenants: int
    active_tenants: int
    total_users: int


class TenantDetailResponse(BaseModel):
    """Detailed tenant info for super_admin view"""
    id: UUID
    name: str
    user_count: int
    status: str = "active"  # "active" or "inactive"
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class UserRoleUpdate(BaseModel):
    role: str


class UserCreateByAdmin(BaseModel):
    """Admin creates a user - no password needed, system generates temp password"""
    email: EmailStr
    role: str = "viewer"


# Assumption Tables schemas

class ColumnDefinition(BaseModel):
    name: str
    data_type: str = "text"
    position: int


class ColumnCreate(BaseModel):
    """Request body for adding a column to an existing table"""
    name: str
    data_type: str = "text"  # text, integer, decimal, date, boolean


class ColumnResponse(BaseModel):
    id: UUID
    name: str
    data_type: str
    position: int
    created_at: datetime

    class Config:
        from_attributes = True


class TableCreate(BaseModel):
    name: str
    description: str | None = None
    effective_date: str | None = None  # ISO date string YYYY-MM-DD
    columns: list[ColumnDefinition] = []


class TableUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    effective_date: str | None = None  # ISO date string YYYY-MM-DD


class TableResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    effective_date: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    columns: list[ColumnResponse] = []

    class Config:
        from_attributes = True


class TableListResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    effective_date: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime | None = None
    column_count: int = 0
    row_count: int = 0

    class Config:
        from_attributes = True


class RowResponse(BaseModel):
    id: UUID
    row_index: int
    cells: dict[str, str | int | float | bool | None]  # column_name: value


class TableDetailResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    effective_date: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    columns: list[ColumnResponse]
    rows: list[RowResponse]
    # Pagination metadata
    total_rows: int | None = None  # Total row count (when paginated)
    offset: int | None = None  # Current offset
    limit: int | None = None  # Page size

    class Config:
        from_attributes = True


# Row CRUD schemas

class RowCreate(BaseModel):
    """Single row with column_name: value pairs"""
    cells: dict[str, str | int | float | bool | None]


class RowsCreate(BaseModel):
    """Request body for adding multiple rows"""
    rows: list[RowCreate]


class RowUpdate(BaseModel):
    """Partial update for row cells"""
    cells: dict[str, str | int | float | bool | None]


# Version schemas

class VersionCreate(BaseModel):
    """Request body for creating a version snapshot"""
    comment: str


class VersionResponse(BaseModel):
    """Version metadata response"""
    id: UUID
    version_number: int
    comment: str
    created_by: UUID
    created_by_name: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class VersionListResponse(BaseModel):
    """Version metadata for list endpoints (without full data)"""
    id: UUID
    version_number: int
    comment: str
    created_by: UUID
    created_by_name: str
    created_at: datetime
    approval_status: str = "draft"  # "draft", "submitted", "approved", "rejected"
    submitted_by: UUID | None = None
    submitted_by_name: str | None = None
    submitted_at: datetime | None = None
    reviewed_by: UUID | None = None
    reviewed_by_name: str | None = None
    reviewed_at: datetime | None = None

    class Config:
        from_attributes = True


class VersionRowResponse(BaseModel):
    """Row data from a version snapshot"""
    row_index: int
    cells: dict[str, str | int | float | bool | None]


class VersionDetailResponse(BaseModel):
    """Full version with metadata and data"""
    id: UUID
    version_number: int
    comment: str
    created_by: UUID
    created_by_name: str | None
    created_at: datetime
    rows: list[VersionRowResponse]
    # Approval status fields (PRD-012)
    approval_status: str = "draft"  # "draft", "submitted", "approved", "rejected"
    submitted_by: UUID | None = None
    submitted_at: datetime | None = None
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None

    class Config:
        from_attributes = True


class ModifiedCellResponse(BaseModel):
    """A cell that changed between versions"""
    row_index: int
    column_name: str
    old_value: str | None
    new_value: str | None


class VersionDiffResponse(BaseModel):
    """Diff between two versions"""
    added_rows: list[int]
    deleted_rows: list[int]
    modified_cells: list[ModifiedCellResponse]


# Visual Diff schemas (PRD-011)

class VersionMetadata(BaseModel):
    """Version metadata for diff response"""
    id: UUID
    version_number: int
    created_by: UUID
    created_by_name: str | None
    created_at: datetime
    comment: str


class DiffSummary(BaseModel):
    """Summary statistics for a diff"""
    total_changes: int
    rows_added: int
    rows_removed: int
    cells_modified: int


class ColumnSummary(BaseModel):
    """Per-column change summary"""
    column_name: str
    change_count: int
    has_additions: bool
    has_removals: bool
    has_modifications: bool


class CellStatus(BaseModel):
    """Cell with change status for row-level context"""
    column_name: str
    value: str | int | float | bool | None = None
    old_value: str | int | float | bool | None = None
    new_value: str | int | float | bool | None = None
    status: str  # "unchanged", "modified", "added", "removed"


class RowChange(BaseModel):
    """A row change entry in the diff"""
    type: str  # "row_added", "row_removed", "row_modified"
    row_index: int
    cells: list[CellStatus] | dict[str, str | int | float | bool | None]


class FormattedDiffResponse(BaseModel):
    """Full formatted diff response for visual comparison"""
    table_id: UUID
    version_a: VersionMetadata
    version_b: VersionMetadata
    summary: DiffSummary
    column_summary: list[ColumnSummary]
    changes: list[RowChange]


# Approval Workflow schemas (PRD-012)

class ApprovalStatus(BaseModel):
    """Approval status for a version"""
    status: str  # "draft", "submitted", "approved", "rejected"
    submitted_by: UUID | None = None
    submitted_at: datetime | None = None
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None


class SubmitApprovalRequest(BaseModel):
    """Request body for submitting a version for approval"""
    comment: str | None = None


class ApproveRequest(BaseModel):
    """Request body for approving a version"""
    comment: str | None = None


class RejectRequest(BaseModel):
    """Request body for rejecting a version - comment is required"""
    comment: str


class ApprovalHistoryEntry(BaseModel):
    """Single entry in the approval history audit trail"""
    id: UUID
    from_status: str | None  # nullable for initial creation
    to_status: str
    changed_by: UUID
    changed_by_name: str | None  # User's email/name for display
    comment: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# CSV Import schemas (PRD-015)

class InferredColumn(BaseModel):
    """Inferred column type from CSV"""
    name: str
    type: str  # "text", "integer", "decimal", "date", "boolean"


class ImportValidationError(BaseModel):
    """A validation error from CSV import"""
    row: int
    column: str
    expected: str
    value: str
    message: str


class ImportPreviewResponse(BaseModel):
    """Preview of what a CSV import will do"""
    inferred_columns: list[InferredColumn]
    row_count: int
    sample_rows: list[dict[str, str]]  # First 10 rows
    validation_warnings: list[ImportValidationError] = []


class ImportResultResponse(BaseModel):
    """Result of a successful CSV import"""
    table_id: UUID
    table_name: str
    column_count: int
    row_count: int


class ImportReplaceResultResponse(BaseModel):
    """Result of a CSV import that replaces existing data"""
    rows_imported: int


class ImportAppendResultResponse(BaseModel):
    """Result of a CSV import that appends data"""
    rows_added: int


# Pending Approvals schemas (PRD-019 US-008)

class PendingApprovalItem(BaseModel):
    """A version pending approval"""
    version_id: UUID
    version_number: int
    table_id: UUID
    table_name: str
    submitted_by: UUID
    submitted_by_name: str
    submitted_at: datetime

    class Config:
        from_attributes = True


class PendingApprovalsResponse(BaseModel):
    """Response containing pending approvals for admin dashboard"""
    total_count: int
    items: list[PendingApprovalItem]


# Dashboard Statistics schemas (PRD-020)

class DashboardStatsResponse(BaseModel):
    """Dashboard statistics for the current tenant"""
    table_count: int  # Total assumption tables in tenant
    recent_activity_count: int  # Tables updated in last 7 days
    version_count: int  # Total version snapshots across all tables
