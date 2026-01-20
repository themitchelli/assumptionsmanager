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


class TenantResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserRoleUpdate(BaseModel):
    role: str


# Assumption Tables schemas

class ColumnDefinition(BaseModel):
    name: str
    data_type: str = "text"
    position: int


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
