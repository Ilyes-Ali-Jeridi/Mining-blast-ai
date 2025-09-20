-- Core data models migration for Automated Drill-and-Blast System
-- Creates Site, BlastRecord, MeasurementData, and Configuration tables
-- Implements requirements 1.7, 9.4, 9.5

-- Create enum types for better data integrity
CREATE TYPE blast_status AS ENUM (
    'draft',
    'pending_review', 
    'approved',
    'executed',
    'measured',
    'archived'
);

CREATE TYPE measurement_type AS ENUM (
    'fragmentation',
    'ppv',
    'vibration',
    'airblast',
    'flyrock',
    'displacement',
    'noise'
);

CREATE TYPE measurement_quality AS ENUM (
    'excellent',
    'good',
    'fair',
    'poor',
    'invalid'
);

CREATE TYPE configuration_type AS ENUM (
    'physics',
    'safety',
    'optimization',
    'explosives',
    'equipment',
    'system',
    'user',
    'site_specific'
);

CREATE TYPE configuration_scope AS ENUM (
    'global',
    'site',
    'user',
    'session'
);

-- Create sites table
CREATE TABLE sites (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    location VARCHAR(500),
    coordinates JSONB, -- {"latitude": float, "longitude": float}
    
    -- Site status and metadata
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    site_type VARCHAR(50) DEFAULT 'open_pit' NOT NULL,
    regulatory_zone VARCHAR(100),
    
    -- Core site data stored as JSONB for flexibility
    bench_geometry JSONB NOT NULL,
    rock_properties JSONB NOT NULL,
    equipment_specs JSONB NOT NULL,
    operational_constraints JSONB NOT NULL,
    safety_config JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create blast_records table
CREATE TABLE blast_records (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    
    -- Basic blast information
    blast_name VARCHAR(200) NOT NULL,
    blast_description TEXT,
    blast_status blast_status DEFAULT 'draft' NOT NULL,
    
    -- Blast execution information
    planned_execution_date TIMESTAMP WITH TIME ZONE,
    actual_execution_date TIMESTAMP WITH TIME ZONE,
    blast_operator VARCHAR(100),
    
    -- Core blast data stored as JSONB
    plan_data JSONB NOT NULL,
    predicted_results JSONB NOT NULL,
    measured_results JSONB,
    safety_validation JSONB NOT NULL,
    engineer_signoff JSONB,
    optimization_metadata JSONB,
    
    -- Version control and audit
    plan_version INTEGER DEFAULT 1 NOT NULL,
    parent_blast_id INTEGER REFERENCES blast_records(id),
    is_template BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create measurement_data table
CREATE TABLE measurement_data (
    id SERIAL PRIMARY KEY,
    blast_record_id INTEGER NOT NULL REFERENCES blast_records(id) ON DELETE CASCADE,
    
    -- Measurement identification
    measurement_name VARCHAR(200) NOT NULL,
    measurement_type measurement_type NOT NULL,
    measurement_quality measurement_quality NOT NULL,
    
    -- Measurement metadata
    measurement_date TIMESTAMP WITH TIME ZONE NOT NULL,
    measurement_method VARCHAR(100) NOT NULL,
    operator_name VARCHAR(100),
    equipment_used VARCHAR(200),
    
    -- Core measurement data stored as JSONB
    measurement_location JSONB,
    measured_values JSONB NOT NULL,
    quality_metrics JSONB,
    file_references JSONB,
    processing_metadata JSONB,
    prediction_comparison JSONB,
    
    -- Notes and validation
    notes TEXT,
    is_validated BOOLEAN DEFAULT FALSE NOT NULL,
    validated_by VARCHAR(100),
    validation_date TIMESTAMP WITH TIME ZONE,
    
    -- Flags for data usage
    use_for_training BOOLEAN DEFAULT TRUE NOT NULL,
    use_for_validation BOOLEAN DEFAULT TRUE NOT NULL,
    is_outlier BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create configurations table (replaces system_configuration with enhanced features)
CREATE TABLE configurations (
    id SERIAL PRIMARY KEY,
    
    -- Configuration identification
    config_key VARCHAR(200) NOT NULL,
    config_name VARCHAR(200) NOT NULL,
    config_description TEXT,
    
    -- Configuration categorization
    config_type configuration_type NOT NULL,
    config_scope configuration_scope DEFAULT 'global' NOT NULL,
    
    -- Scope-specific identifiers
    site_id INTEGER REFERENCES sites(id),
    user_id VARCHAR(100),
    
    -- Configuration data
    config_value JSONB NOT NULL,
    
    -- Version control
    version INTEGER DEFAULT 1 NOT NULL,
    parent_config_id INTEGER REFERENCES configurations(id),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_default BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Validation and approval
    is_validated BOOLEAN DEFAULT FALSE NOT NULL,
    validated_by VARCHAR(100),
    validation_date TIMESTAMP WITH TIME ZONE,
    validation_notes TEXT,
    
    -- Change tracking
    created_by VARCHAR(100),
    modified_by VARCHAR(100),
    change_reason TEXT,
    
    -- Metadata
    tags JSONB, -- Array of tags for categorization
    dependencies JSONB, -- Array of dependent configuration keys
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create indexes for performance

-- Sites indexes
CREATE INDEX idx_sites_name ON sites(name);
CREATE INDEX idx_sites_name_active ON sites(name, is_active);
CREATE INDEX idx_sites_location ON sites(location);
CREATE INDEX idx_sites_type_active ON sites(site_type, is_active);
CREATE INDEX idx_sites_created_at ON sites(created_at);

-- Blast records indexes
CREATE INDEX idx_blast_records_site_id ON blast_records(site_id);
CREATE INDEX idx_blast_records_blast_name ON blast_records(blast_name);
CREATE INDEX idx_blast_records_status ON blast_records(blast_status);
CREATE INDEX idx_blast_records_execution_date ON blast_records(planned_execution_date);
CREATE INDEX idx_blast_records_created_at ON blast_records(created_at);
CREATE INDEX idx_blast_records_parent_blast ON blast_records(parent_blast_id);

-- Measurement data indexes
CREATE INDEX idx_measurement_data_blast_record ON measurement_data(blast_record_id);
CREATE INDEX idx_measurement_data_type ON measurement_data(measurement_type);
CREATE INDEX idx_measurement_data_quality ON measurement_data(measurement_quality);
CREATE INDEX idx_measurement_data_date ON measurement_data(measurement_date);
CREATE INDEX idx_measurement_data_training ON measurement_data(use_for_training, is_outlier);
CREATE INDEX idx_measurement_data_validated ON measurement_data(is_validated);

-- Configurations indexes
CREATE INDEX idx_configurations_key ON configurations(config_key);
CREATE INDEX idx_config_key_scope ON configurations(config_key, config_scope);
CREATE INDEX idx_config_type_active ON configurations(config_type, is_active);
CREATE INDEX idx_config_site_user ON configurations(site_id, user_id);
CREATE INDEX idx_configurations_created_at ON configurations(created_at);

-- Create triggers for updated_at timestamps
CREATE TRIGGER update_sites_updated_at 
    BEFORE UPDATE ON sites 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_blast_records_updated_at 
    BEFORE UPDATE ON blast_records 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_measurement_data_updated_at 
    BEFORE UPDATE ON measurement_data 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_configurations_updated_at 
    BEFORE UPDATE ON configurations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS) for all tables
ALTER TABLE sites ENABLE ROW LEVEL SECURITY;
ALTER TABLE blast_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE measurement_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE configurations ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for sites
CREATE POLICY "Allow read access to sites for authenticated users" ON sites
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all operations on sites for service role" ON sites
    FOR ALL USING (auth.role() = 'service_role');

-- Create RLS policies for blast_records
CREATE POLICY "Allow read access to blast_records for authenticated users" ON blast_records
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all operations on blast_records for service role" ON blast_records
    FOR ALL USING (auth.role() = 'service_role');

-- Create RLS policies for measurement_data
CREATE POLICY "Allow read access to measurement_data for authenticated users" ON measurement_data
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all operations on measurement_data for service role" ON measurement_data
    FOR ALL USING (auth.role() = 'service_role');

-- Create RLS policies for configurations
CREATE POLICY "Allow read access to configurations for authenticated users" ON configurations
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all operations on configurations for service role" ON configurations
    FOR ALL USING (auth.role() = 'service_role');

-- Grant necessary permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- Insert default configurations to replace system_configuration data
INSERT INTO configurations (config_key, config_name, config_type, config_scope, config_value, is_default, is_validated, created_by) VALUES
('default_physics_parameters', 'Default Physics Parameters', 'physics', 'global', '{
    "kuz_ram": {
        "rock_factor_a": 7.0,
        "uniformity_index": 1.25,
        "calibration_data": []
    },
    "ppv": {
        "k": 1.4,
        "a": 0.333,
        "b": 1.6,
        "site_specific_constants": {}
    },
    "fragmentation_curves": {
        "default_distribution": "rosin_rammler",
        "rosin_rammler": {
            "default_n": 1.25
        },
        "swebrec": {
            "default_b": 1.5,
            "default_x0": 50.0
        }
    }
}', true, true, 'system');

INSERT INTO configurations (config_key, config_name, config_type, config_scope, config_value, is_default, is_validated, created_by) VALUES
('default_safety_limits', 'Default Safety Limits', 'safety', 'global', '{
    "charge_limits": {
        "max_charge_per_hole": 50.0,
        "max_charge_per_delay": 200.0,
        "safety_factor": 1.0
    },
    "powder_factor_limits": {
        "min_powder_factor": 0.05,
        "max_powder_factor": 1.5,
        "recommended_range": [0.2, 0.8]
    },
    "ppv_limits": {
        "default_limit": 5.0,
        "structure_limits": {
            "residential": 2.0,
            "commercial": 5.0,
            "industrial": 10.0,
            "sensitive": 1.0
        }
    },
    "distance_limits": {
        "min_distance_to_structures": 100.0,
        "min_distance_to_roads": 50.0,
        "exclusion_zone_buffer": 25.0
    },
    "regulatory_compliance": {
        "jurisdiction": "Generic",
        "regulation_reference": "Default safety standards",
        "last_updated": "2024-01-01",
        "compliance_notes": "Default conservative safety limits"
    }
}', true, true, 'system');

INSERT INTO configurations (config_key, config_name, config_type, config_scope, config_value, is_default, is_validated, created_by) VALUES
('default_optimization_settings', 'Default Optimization Settings', 'optimization', 'global', '{
    "algorithms": {
        "default_algorithm": "cp_sat",
        "algorithm_preferences": {
            "cp_sat": {
                "max_time_seconds": 300,
                "num_search_workers": 4,
                "log_search_progress": false
            },
            "scipy": {
                "method": "differential_evolution",
                "max_iterations": 1000,
                "tolerance": 1e-6,
                "polish": true
            },
            "genetic": {
                "population_size": 50,
                "num_generations": 100,
                "mutation_rate": 0.1,
                "crossover_rate": 0.8
            }
        }
    },
    "objectives": {
        "default_weights": {
            "fragmentation": 1.0,
            "cost": 0.5,
            "ppv": 2.0,
            "uniformity": 0.3
        },
        "convergence_criteria": {
            "max_runtime_seconds": 600,
            "objective_tolerance": 0.001,
            "stagnation_generations": 20
        }
    },
    "constraints": {
        "default_bounds": {
            "burden_range": [2.0, 8.0],
            "spacing_range": [2.0, 8.0],
            "charge_range": [5.0, 50.0],
            "delay_range": [0, 1000]
        }
    }
}', true, true, 'system');

INSERT INTO configurations (config_key, config_name, config_type, config_scope, config_value, is_default, is_validated, created_by) VALUES
('default_explosives_catalog', 'Default Explosives Catalog', 'explosives', 'global', '{
    "catalog": [
        {
            "id": "anfo_standard",
            "name": "Standard ANFO",
            "manufacturer": "Generic",
            "type": "ANFO",
            "density": 850.0,
            "rws": 100.0,
            "vod": 4500.0,
            "energy": 3.7,
            "cost_per_kg": 1.50,
            "availability": {
                "regions": ["global"],
                "lead_time_days": 7,
                "minimum_order": 1000.0
            },
            "regulatory": {
                "max_per_hole": 50.0,
                "max_per_delay": 200.0,
                "storage_class": "1.1D",
                "transport_class": "1.1D"
            },
            "performance": {
                "temperature_range": [-20.0, 50.0],
                "water_resistance": "poor",
                "fume_class": 1,
                "sensitivity": "low"
            },
            "is_active": true
        },
        {
            "id": "emulsion_standard",
            "name": "Standard Emulsion",
            "manufacturer": "Generic",
            "type": "Emulsion",
            "density": 1200.0,
            "rws": 115.0,
            "vod": 5200.0,
            "energy": 4.2,
            "cost_per_kg": 2.25,
            "availability": {
                "regions": ["global"],
                "lead_time_days": 5,
                "minimum_order": 500.0
            },
            "regulatory": {
                "max_per_hole": 45.0,
                "max_per_delay": 180.0,
                "storage_class": "1.1D",
                "transport_class": "1.1D"
            },
            "performance": {
                "temperature_range": [-30.0, 60.0],
                "water_resistance": "excellent",
                "fume_class": 1,
                "sensitivity": "medium"
            },
            "is_active": true
        }
    ],
    "default_selections": {
        "primary_explosive": "emulsion_standard",
        "secondary_explosive": "anfo_standard",
        "stemming_material": "drill_cuttings"
    }
}', true, true, 'system');

-- Add comments for documentation
COMMENT ON TABLE sites IS 'Site configuration and geometry storage with comprehensive site data';
COMMENT ON TABLE blast_records IS 'Historical blast plans and results with complete audit trail';
COMMENT ON TABLE measurement_data IS 'Post-blast measurements for learning and validation';
COMMENT ON TABLE configurations IS 'System configuration storage with versioning and validation';

COMMENT ON COLUMN sites.bench_geometry IS 'JSONB: Bench geometry including elevations, dimensions, and exclusion zones';
COMMENT ON COLUMN sites.rock_properties IS 'JSONB: Rock properties - uniform or block model with UCS, density, etc.';
COMMENT ON COLUMN sites.equipment_specs IS 'JSONB: Drill rigs and explosives catalog specifications';
COMMENT ON COLUMN sites.operational_constraints IS 'JSONB: Drilling constraints, powder factor limits, and sensitive receptors';

COMMENT ON COLUMN blast_records.plan_data IS 'JSONB: Complete blast plan with holes, geometry, and explosive summary';
COMMENT ON COLUMN blast_records.predicted_results IS 'JSONB: Physics model predictions for fragmentation and PPV';
COMMENT ON COLUMN blast_records.measured_results IS 'JSONB: Post-blast measurements and performance assessment';
COMMENT ON COLUMN blast_records.safety_validation IS 'JSONB: Safety validation results and constraint checks';
COMMENT ON COLUMN blast_records.engineer_signoff IS 'JSONB: Engineer sign-off with certification and digital signature';

COMMENT ON COLUMN measurement_data.measured_values IS 'JSONB: Core measurement values varying by measurement type';
COMMENT ON COLUMN measurement_data.quality_metrics IS 'JSONB: Quality assessment and confidence scoring';
COMMENT ON COLUMN measurement_data.file_references IS 'JSONB: References to images, sensor data files, and analysis outputs';
COMMENT ON COLUMN measurement_data.processing_metadata IS 'JSONB: Processing method, software used, and validation checks';

COMMENT ON COLUMN configurations.config_value IS 'JSONB: Configuration data structure varying by configuration type';