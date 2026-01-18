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
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Assumption table versions
CREATE TABLE assumption_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    table_id UUID NOT NULL REFERENCES assumption_tables(id),
    version_number INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    created_by UUID REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    effective_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(table_id, version_number)
);

-- Assumption data (the actual values)
CREATE TABLE assumption_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    version_id UUID NOT NULL REFERENCES assumption_versions(id),
    row_index INTEGER NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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
CREATE INDEX idx_assumption_versions_tenant ON assumption_versions(tenant_id);
CREATE INDEX idx_assumption_versions_table ON assumption_versions(table_id);
CREATE INDEX idx_assumption_data_tenant ON assumption_data(tenant_id);
CREATE INDEX idx_assumption_data_version ON assumption_data(version_id);
CREATE INDEX idx_audit_log_tenant ON audit_log(tenant_id);

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE assumption_tables ENABLE ROW LEVEL SECURITY;
ALTER TABLE assumption_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE assumption_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Create app user for backend connections
CREATE USER app_user WITH PASSWORD 'app_password';

-- RLS Policies - users can only see their tenant's data
CREATE POLICY tenant_isolation_users ON users
    FOR ALL USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE POLICY tenant_isolation_tables ON assumption_tables
    FOR ALL USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE POLICY tenant_isolation_versions ON assumption_versions
    FOR ALL USING (tenant_id = current_setting('app.current_tenant')::UUID);

CREATE POLICY tenant_isolation_data ON assumption_data
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
