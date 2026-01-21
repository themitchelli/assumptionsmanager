/**
 * TypeScript interfaces for API request/response types
 *
 * These match the backend schemas defined in backend/schemas.py
 */

// ============================================================
// Auth Types
// ============================================================

export interface LoginRequest {
	email: string;
	password: string;
}

export interface LoginResponse {
	access_token: string;
	token_type: string;
}

export interface RegisterRequest {
	email: string;
	password: string;
	tenant_id: string;
	name?: string;
}

export interface UserResponse {
	id: string;
	email: string;
	name?: string;
	role: 'viewer' | 'analyst' | 'admin' | 'super_admin';
	tenant_id: string;
	created_at: string;
}

// ============================================================
// Tenant Types
// ============================================================

export interface TenantResponse {
	id: string;
	name: string;
	status?: string;
	created_at: string;
}

export interface TenantListItem {
	id: string;
	name: string;
	user_count: number;
	status: 'active' | 'inactive';
	created_at: string;
}

export interface TenantListResponse {
	tenants: TenantListItem[];
}

export interface PlatformStatsResponse {
	total_tenants: number;
	active_tenants: number;
	total_users: number;
}

export interface TenantDetailResponse {
	id: string;
	name: string;
	user_count: number;
	status: 'active' | 'inactive';
	created_at: string;
	updated_at?: string;
}

export interface CreateTenantRequest {
	name: string;
}

export interface CreateTenantWithAdminRequest {
	name: string;
	admin_email: string;
	admin_name: string;
}

export interface TenantCreateResponse {
	id: string;
	name: string;
	created_at: string;
	admin_id: string;
	admin_email: string;
}

export interface UpdateTenantRequest {
	name?: string;
	status?: 'active' | 'inactive';
}

// ============================================================
// User Management Types
// ============================================================

export interface CreateUserRequest {
	email: string;
	role: 'viewer' | 'analyst' | 'admin';
}

export interface UpdateUserRequest {
	role?: 'viewer' | 'analyst' | 'admin';
}

// ============================================================
// Assumption Table Types
// ============================================================

export interface ColumnDefinition {
	name: string;
	data_type: 'text' | 'integer' | 'decimal' | 'date' | 'boolean';
	position: number;
}

export interface ColumnResponse extends ColumnDefinition {
	id: string;
	created_at?: string;
}

export interface CreateColumnRequest {
	name: string;
	data_type: 'text' | 'integer' | 'decimal' | 'date' | 'boolean';
}

export interface CreateTableRequest {
	name: string;
	description?: string;
	effective_date?: string;
	columns: ColumnDefinition[];
}

export interface TableResponse {
	id: string;
	tenant_id: string;
	name: string;
	description?: string;
	effective_date?: string;
	created_by: string;
	created_at: string;
	updated_at?: string;
	columns: ColumnResponse[];
}

export interface UpdateTableRequest {
	name?: string;
	description?: string;
	effective_date?: string;
}

export interface TableListResponse {
	id: string;
	name: string;
	description?: string;
	effective_date?: string;
	created_by: string;
	created_at: string;
	updated_at?: string;
	column_count: number;
	row_count: number;
}

export interface CellData {
	[columnName: string]: string | number | boolean | null;
}

export interface RowResponse {
	id: string;
	row_index: number;
	cells: CellData;
}

export interface TableDetailResponse extends TableListResponse {
	columns: ColumnResponse[];
	rows: RowResponse[];
}

export interface CreateRowsRequest {
	rows: CellData[];
}

export interface UpdateRowRequest {
	[columnName: string]: string | number | boolean | null;
}

// ============================================================
// Version Types
// ============================================================

export interface CreateVersionRequest {
	comment: string;
}

export interface VersionListResponse {
	id: string;
	version_number: number;
	comment: string;
	created_by: string;
	created_by_name?: string;
	created_at: string;
	approval_status?: 'draft' | 'submitted' | 'approved' | 'rejected';
	submitted_by?: string;
	submitted_by_name?: string;
	submitted_at?: string;
	reviewed_by?: string;
	reviewed_by_name?: string;
	reviewed_at?: string;
}

export interface VersionDetailResponse extends VersionListResponse {
	rows: RowResponse[];
	submitted_by?: string;
	submitted_at?: string;
	reviewed_by?: string;
	reviewed_at?: string;
}

// ============================================================
// Diff Types
// ============================================================

export interface DiffCell {
	column_name: string;
	old_value?: string | number | boolean | null;
	new_value?: string | number | boolean | null;
	value?: string | number | boolean | null;
	status: 'unchanged' | 'modified' | 'added' | 'removed';
}

export interface RowChange {
	type: 'row_added' | 'row_removed' | 'row_modified';
	row_index: number;
	cells: DiffCell[] | CellData;
}

export interface ColumnSummary {
	column_name: string;
	change_count: number;
	has_additions: boolean;
	has_removals: boolean;
	has_modifications: boolean;
}

export interface DiffSummary {
	total_changes: number;
	rows_added: number;
	rows_removed: number;
	cells_modified: number;
}

export interface VersionMetadata {
	id: string;
	version_number: number;
	created_by: string;
	created_by_name?: string;
	created_at: string;
	comment: string;
}

export interface FormattedDiffResponse {
	table_id: string;
	version_a: VersionMetadata;
	version_b: VersionMetadata;
	summary: DiffSummary;
	column_summary: ColumnSummary[];
	changes: RowChange[];
}

// ============================================================
// Approval Types
// ============================================================

export interface SubmitApprovalRequest {
	comment?: string;
}

export interface ApproveRequest {
	comment?: string;
}

export interface RejectRequest {
	comment: string;
}

export interface ApprovalHistoryEntry {
	id: string;
	from_status: 'draft' | 'submitted' | 'approved' | 'rejected' | null;
	to_status: 'draft' | 'submitted' | 'approved' | 'rejected';
	changed_by: string;
	changed_by_name: string;
	comment?: string;
	created_at: string;
}

// ============================================================
// Import Types
// ============================================================

export interface ImportPreviewColumn {
	name: string;
	inferred_type: 'text' | 'integer' | 'decimal' | 'date' | 'boolean';
}

export interface ImportValidationError {
	row: number;
	column: string;
	expected: string;
	value: string;
	message: string;
}

export interface ImportPreviewResponse {
	columns: ImportPreviewColumn[];
	row_count: number;
	preview_rows: CellData[];
	errors: ImportValidationError[];
}

export interface ImportResponse {
	table_id: string;
	table_name: string;
	column_count: number;
	row_count: number;
}

export interface AppendImportResponse {
	rows_added: number;
}

// ============================================================
// Pending Approvals Types
// ============================================================

export interface PendingApprovalItem {
	version_id: string;
	version_number: number;
	table_id: string;
	table_name: string;
	submitted_by: string;
	submitted_by_name: string;
	submitted_at: string;
}

export interface PendingApprovalsResponse {
	total_count: number;
	items: PendingApprovalItem[];
}

// ============================================================
// Dashboard Statistics Types
// ============================================================

export interface DashboardStatsResponse {
	table_count: number;
	recent_activity_count: number;
	version_count: number;
}
