-- Authentication and authorization tables migration
-- Implements requirements 4.4, 4.5, 4.7 for user management and audit trails

-- Create user role enum
CREATE TYPE user_role AS ENUM ('engineer', 'admin', 'operator', 'viewer');

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE NOT NULL,
    role user_role DEFAULT 'viewer' NOT NULL,
    
    -- Professional credentials (required for engineer sign-off)
    professional_license VARCHAR(100),
    license_expiry TIMESTAMP WITH TIME ZONE,
    organization VARCHAR(200),
    employee_id VARCHAR(50),
    
    -- Security settings
    password_changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    last_login_at TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INTEGER DEFAULT 0 NOT NULL,
    locked_until TIMESTAMP WITH TIME ZONE,
    
    -- Two-factor authentication (future enhancement)
    two_factor_enabled BOOLEAN DEFAULT FALSE NOT NULL,
    two_factor_secret VARCHAR(255),
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create indexes for users table
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_professional_license ON users(professional_license);

-- Sessions table
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Session metadata
    ip_address INET,
    user_agent TEXT,
    device_info JSONB,
    
    -- Session lifecycle
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    
    -- Security flags
    is_admin_session BOOLEAN DEFAULT FALSE NOT NULL,
    requires_2fa BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create indexes for sessions table
CREATE INDEX idx_sessions_token ON sessions(session_token);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX idx_sessions_is_active ON sessions(is_active);

-- Audit logs table
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    
    -- User and session information
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    
    -- Action details
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(100),
    
    -- Request details
    endpoint VARCHAR(200),
    method VARCHAR(10),
    ip_address INET,
    user_agent TEXT,
    
    -- Action metadata
    action_data JSONB,
    result VARCHAR(20) NOT NULL,
    error_message TEXT,
    
    -- Timing
    duration_ms INTEGER,
    
    -- Security and compliance
    risk_level VARCHAR(20) DEFAULT 'LOW' NOT NULL,
    compliance_flags JSONB,
    
    -- Audit fields (immutable)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create indexes for audit_logs table
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX idx_audit_logs_resource_id ON audit_logs(resource_id);
CREATE INDEX idx_audit_logs_result ON audit_logs(result);
CREATE INDEX idx_audit_logs_risk_level ON audit_logs(risk_level);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at 
    BEFORE UPDATE ON sessions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create default admin user (password: AdminPass123!)
-- Note: In production, this should be changed immediately
INSERT INTO users (
    username, 
    email, 
    full_name, 
    hashed_password, 
    role, 
    is_active, 
    is_verified,
    professional_license,
    organization
) VALUES (
    'admin',
    'admin@drill-blast-system.com',
    'System Administrator',
    '$2b$12$LQv3c1yqBWVHxkd0LQ4YNu.5rAifsboFI8106O6Id8HQ2k2MFUO2G', -- AdminPass123!
    'admin',
    TRUE,
    TRUE,
    'ADMIN-001',
    'Drill-Blast System'
);

-- Create sample engineer user (password: EngineerPass123!)
INSERT INTO users (
    username, 
    email, 
    full_name, 
    hashed_password, 
    role, 
    is_active, 
    is_verified,
    professional_license,
    license_expiry,
    organization,
    employee_id
) VALUES (
    'engineer_demo',
    'engineer@drill-blast-system.com',
    'Dr. Jane Smith, P.Eng',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPDw96.6.', -- EngineerPass123!
    'engineer',
    TRUE,
    TRUE,
    'PE-12345',
    '2025-12-31 23:59:59+00',
    'Mining Engineering Corp',
    'ENG-001'
);

-- Add RLS (Row Level Security) policies for multi-tenancy (optional)
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Grant permissions to application role (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON users TO drill_blast_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON sessions TO drill_blast_app;
-- GRANT SELECT, INSERT ON audit_logs TO drill_blast_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO drill_blast_app;

-- Add comments for documentation
COMMENT ON TABLE users IS 'User accounts for authentication and authorization';
COMMENT ON TABLE sessions IS 'Active user sessions for session management';
COMMENT ON TABLE audit_logs IS 'Immutable audit trail for compliance and security monitoring';

COMMENT ON COLUMN users.professional_license IS 'Professional engineering license number (required for engineers)';
COMMENT ON COLUMN users.license_expiry IS 'Professional license expiry date';
COMMENT ON COLUMN audit_logs.compliance_flags IS 'JSON flags for regulatory compliance tracking';
COMMENT ON COLUMN audit_logs.risk_level IS 'Security risk level: LOW, MEDIUM, HIGH, CRITICAL';