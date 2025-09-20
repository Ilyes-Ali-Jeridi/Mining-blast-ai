-- Initial schema for Automated Drill-and-Blast System
-- This migration creates the core tables for the system

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create audit_log table for compliance and debugging
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    user_id VARCHAR(100),
    session_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for audit_log
CREATE INDEX idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_session_id ON audit_log(session_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- Create system_configuration table for application settings
CREATE TABLE system_configuration (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value JSONB NOT NULL,
    config_type VARCHAR(50) NOT NULL,
    description TEXT,
    version INTEGER DEFAULT 1 NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for system_configuration
CREATE INDEX idx_system_config_key ON system_configuration(config_key);
CREATE INDEX idx_system_config_type ON system_configuration(config_type);
CREATE INDEX idx_system_config_active ON system_configuration(is_active);

-- Insert default physics parameters
INSERT INTO system_configuration (config_key, config_value, config_type, description, version, is_active) VALUES
('default_physics_parameters', '{
    "kuz_ram": {
        "rock_factor_a": 7.0,
        "uniformity_index": 1.25
    },
    "ppv": {
        "k": 1.4,
        "a": 0.333,
        "b": 1.6
    }
}', 'physics', 'Default physics model parameters', 1, true);

-- Insert default safety limits
INSERT INTO system_configuration (config_key, config_value, config_type, description, version, is_active) VALUES
('default_safety_limits', '{
    "max_charge_per_hole": 50.0,
    "max_charge_per_delay": 200.0,
    "powder_factor_min": 0.05,
    "powder_factor_max": 1.5,
    "ppv_default_limit": 5.0
}', 'safety', 'Default safety constraint limits', 1, true);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_audit_log_updated_at BEFORE UPDATE ON audit_log 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_configuration_updated_at BEFORE UPDATE ON system_configuration 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS) for security
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_configuration ENABLE ROW LEVEL SECURITY;

-- Create policies for audit_log (read-only for authenticated users)
CREATE POLICY "Allow read access to audit_log for authenticated users" ON audit_log
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Allow insert to audit_log for service role" ON audit_log
    FOR INSERT WITH CHECK (auth.role() = 'service_role');

-- Create policies for system_configuration
CREATE POLICY "Allow read access to system_configuration for authenticated users" ON system_configuration
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all operations on system_configuration for service role" ON system_configuration
    FOR ALL USING (auth.role() = 'service_role');

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;