-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tenants table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);

-- Assumption tables metadata
CREATE TABLE assumption_tables (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    effective_date DATE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Column definitions for each assumption table (flexible schema)
CREATE TABLE assumption_columns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_id UUID NOT NULL REFERENCES assumption_tables(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    data_type VARCHAR(20) NOT NULL DEFAULT 'text' CHECK (data_type IN ('text', 'integer', 'decimal', 'date', 'boolean')),
    position INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(table_id, name),
    UNIQUE(table_id, position)
);

-- Row containers for cell data
CREATE TABLE assumption_rows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_id UUID NOT NULL REFERENCES assumption_tables(id) ON DELETE CASCADE,
    row_index INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(table_id, row_index)
);

-- Individual cell values
CREATE TABLE assumption_cells (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    row_id UUID NOT NULL REFERENCES assumption_rows(id) ON DELETE CASCADE,
    column_id UUID NOT NULL REFERENCES assumption_columns(id) ON DELETE CASCADE,
    value TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(row_id, column_id)
);

-- Version snapshots for assumption tables
CREATE TABLE assumption_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_id UUID NOT NULL REFERENCES assumption_tables(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    comment TEXT NOT NULL,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    context JSONB DEFAULT '{}',
    UNIQUE(table_id, version_number)
);

-- Immutable cell snapshots - copied from assumption_cells at version creation
CREATE TABLE assumption_version_cells (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id UUID NOT NULL REFERENCES assumption_versions(id) ON DELETE CASCADE,
    column_id UUID NOT NULL,
    column_name TEXT NOT NULL,
    row_index INTEGER NOT NULL,
    value TEXT
);

-- Audit log
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_assumption_tables_tenant ON assumption_tables(tenant_id);
CREATE INDEX idx_assumption_columns_table ON assumption_columns(table_id);
CREATE INDEX idx_assumption_rows_table ON assumption_rows(table_id);
CREATE INDEX idx_assumption_cells_row ON assumption_cells(row_id);
CREATE INDEX idx_assumption_cells_column ON assumption_cells(column_id);
CREATE INDEX idx_audit_log_tenant ON audit_log(tenant_id);
CREATE INDEX idx_assumption_versions_table ON assumption_versions(table_id);
CREATE INDEX idx_assumption_version_cells_version ON assumption_version_cells(version_id);
CREATE INDEX idx_assumption_version_cells_version_row ON assumption_version_cells(version_id, row_index);

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE assumption_tables ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Create app user for backend connections
CREATE USER app_user WITH PASSWORD 'app_password';

-- RLS Policies - users can only see their tenant's data
CREATE POLICY tenant_isolation_users ON users
    FOR ALL USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE POLICY tenant_isolation_tables ON assumption_tables
    FOR ALL USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE POLICY tenant_isolation_audit ON audit_log
    FOR ALL USING (tenant_id = current_setting('app.current_tenant')::UUID);

-- Grant permissions to app_user
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Insert demo tenant
INSERT INTO tenants (id, name) VALUES
    ('11111111-1111-1111-1111-111111111111', 'Demo Company');
