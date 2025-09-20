"""
Unit tests for repository classes.
Tests CRUD operations and specialized query methods.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.drill_blast_system.core.database import Base
from src.drill_blast_system.models.site import Site
from src.drill_blast_system.models.blast_record import BlastRecord, BlastStatus
from src.drill_blast_system.models.measurement_data import MeasurementData, MeasurementType, MeasurementQuality
from src.drill_blast_system.models.configuration import Configuration, ConfigurationType, ConfigurationScope
from src.drill_blast_system.repositories.site import SiteRepository
from src.drill_blast_system.repositories.blast_record import BlastRecordRepository
from src.drill_blast_system.repositories.measurement_data import MeasurementDataRepository
from src.drill_blast_system.repositories.configuration import ConfigurationRepository


# Test database setup
@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_site_data():
    """Sample site data for testing."""
    return {
        "name": "Test Site",
        "description": "Test site for unit tests",
        "location": "Test Location",
        "coordinates": {"latitude": -33.8688, "longitude": 151.2093},
        "is_active": True,
        "site_type": "open_pit",
        "bench_geometry": {
            "bench_top_elevation": 200.0,
            "bench_bottom_elevation": 185.0,
            "bench_width": 50.0,
            "bench_length": 100.0,
            "free_face_orientation": 45.0
        },
        "rock_properties": {
            "is_uniform": True,
            "uniform_properties": {
                "rock_type": "granite",
                "ucs": 150.0,
                "density": 2650.0,
                "rock_factor_a": 7.0
            }
        },
        "equipment_specs": {
            "drill_rigs": [],
            "explosives_catalog": []
        },
        "operational_constraints": {
            "drilling_constraints": {
                "min_burden": 2.0,
                "max_burden": 8.0,
                "min_spacing": 2.0,
                "max_spacing": 8.0
            },
            "powder_factor_limits": {
                "min_powder_factor": 0.1,
                "max_powder_factor": 1.0
            }
        }
    }


@pytest.fixture
def sample_blast_data():
    """Sample blast record data for testing."""
    return {
        "site_id": 1,
        "blast_name": "Test Blast 001",
        "blast_description": "Test blast for unit tests",
        "blast_status": BlastStatus.DRAFT,
        "plan_data": {
            "holes": [
                {
                    "hole_id": "H001",
                    "coordinates": {"x": 1000.0, "y": 2000.0, "z": 200.0},
                    "depth": 16.5,
                    "diameter": 165.0,
                    "charge_kg": 35.2,
                    "stemming_m": 4.0,
                    "delay_ms": 0,
                    "explosive_type": "ANFO",
                    "drill_rig": "Test Rig",
                    "collar_elevation": 200.0,
                    "toe_elevation": 183.5,
                    "burden": 4.5,
                    "spacing": 5.0,
                    "subdrill": 1.5,
                    "hole_angle": 90.0,
                    "hole_azimuth": 0.0
                }
            ],
            "blast_geometry": {
                "total_holes": 1,
                "total_depth": 16.5,
                "blast_area": 22.5,
                "blast_volume": 337.5,
                "rock_tonnage": 894.4,
                "average_burden": 4.5,
                "average_spacing": 5.0,
                "hole_pattern": "rectangular"
            },
            "explosive_summary": {
                "total_explosive": 35.2,
                "powder_factor_kg_t": 0.39,
                "powder_factor_kg_m3": 0.10,
                "explosive_types_used": ["ANFO"],
                "max_charge_per_hole": 35.2,
                "max_charge_per_delay": 35.2
            }
        },
        "predicted_results": {
            "fragmentation": {
                "mean_fragment_size": 125.0,
                "p10": 45.0,
                "p50": 95.0,
                "p80": 180.0,
                "uniformity_index": 1.25,
                "characteristic_size": 110.0,
                "distribution_type": "rosin_rammler"
            },
            "ppv_predictions": {
                "max_predicted_ppv": 2.1,
                "ppv_model_parameters": {"k": 1.4, "a": 0.333, "b": 1.6}
            },
            "model_metadata": {
                "physics_model_version": "1.0.0",
                "prediction_timestamp": datetime.utcnow().isoformat()
            }
        },
        "safety_validation": {
            "validation_timestamp": datetime.utcnow(),
            "is_valid": True,
            "safety_checks": [],
            "violations": [],
            "safety_config_used": {
                "max_charge_per_hole": 50.0,
                "max_charge_per_delay": 200.0
            }
        }
    }


@pytest.fixture
def sample_measurement_data():
    """Sample measurement data for testing."""
    return {
        "blast_record_id": 1,
        "measurement_name": "Test Fragmentation Measurement",
        "measurement_type": MeasurementType.FRAGMENTATION,
        "measurement_quality": MeasurementQuality.GOOD,
        "measurement_date": datetime.utcnow(),
        "measurement_method": "image_analysis",
        "operator_name": "Test Operator",
        "measured_values": {
            "p10": 45.2,
            "p50": 95.8,
            "p80": 185.3,
            "fragment_count": 1247
        },
        "use_for_training": True,
        "use_for_validation": True,
        "is_outlier": False
    }


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing."""
    return {
        "config_key": "test_physics_parameters",
        "config_name": "Test Physics Parameters",
        "config_description": "Test physics configuration",
        "config_type": ConfigurationType.PHYSICS,
        "config_scope": ConfigurationScope.GLOBAL,
        "config_value": {
            "kuz_ram": {
                "rock_factor_a": 7.0,
                "uniformity_index": 1.25
            },
            "ppv": {
                "k": 1.4,
                "a": 0.333,
                "b": 1.6
            }
        },
        "is_active": True,
        "is_default": False,
        "is_validated": True
    }


class TestSiteRepository:
    """Test cases for SiteRepository."""
    
    def test_create_site(self, db_session, sample_site_data):
        """Test site creation."""
        repo = SiteRepository(db_session)
        site = repo.create(sample_site_data)
        
        assert site.id is not None
        assert site.name == "Test Site"
        assert site.is_active is True
        assert site.bench_height == 15.0  # 200 - 185
    
    def test_get_active_sites(self, db_session, sample_site_data):
        """Test getting active sites."""
        repo = SiteRepository(db_session)
        
        # Create active site
        active_site = repo.create(sample_site_data)
        
        # Create inactive site
        inactive_data = sample_site_data.copy()
        inactive_data["name"] = "Inactive Site"
        inactive_data["is_active"] = False
        repo.create(inactive_data)
        
        active_sites = repo.get_active_sites()
        
        assert len(active_sites) == 1
        assert active_sites[0].id == active_site.id
    
    def test_get_by_name(self, db_session, sample_site_data):
        """Test getting site by name."""
        repo = SiteRepository(db_session)
        created_site = repo.create(sample_site_data)
        
        found_site = repo.get_by_name("Test Site")
        
        assert found_site is not None
        assert found_site.id == created_site.id
    
    def test_validate_site_data(self, db_session, sample_site_data):
        """Test site data validation."""
        repo = SiteRepository(db_session)
        site = repo.create(sample_site_data)
        
        validation_results = repo.validate_site_data(site.id)
        
        assert "errors" in validation_results
        assert "warnings" in validation_results
        assert "info" in validation_results


class TestBlastRecordRepository:
    """Test cases for BlastRecordRepository."""
    
    def test_create_blast_record(self, db_session, sample_site_data, sample_blast_data):
        """Test blast record creation."""
        # Create site first
        site_repo = SiteRepository(db_session)
        site = site_repo.create(sample_site_data)
        
        # Create blast record
        blast_repo = BlastRecordRepository(db_session)
        sample_blast_data["site_id"] = site.id
        blast = blast_repo.create(sample_blast_data)
        
        assert blast.id is not None
        assert blast.blast_name == "Test Blast 001"
        assert blast.blast_status == BlastStatus.DRAFT
        assert blast.total_holes == 1
    
    def test_get_by_status(self, db_session, sample_site_data, sample_blast_data):
        """Test getting blasts by status."""
        # Create site and blast
        site_repo = SiteRepository(db_session)
        site = site_repo.create(sample_site_data)
        
        blast_repo = BlastRecordRepository(db_session)
        sample_blast_data["site_id"] = site.id
        blast = blast_repo.create(sample_blast_data)
        
        draft_blasts = blast_repo.get_by_status(BlastStatus.DRAFT)
        
        assert len(draft_blasts) == 1
        assert draft_blasts[0].id == blast.id
    
    def test_update_blast_status(self, db_session, sample_site_data, sample_blast_data):
        """Test updating blast status."""
        # Create site and blast
        site_repo = SiteRepository(db_session)
        site = site_repo.create(sample_site_data)
        
        blast_repo = BlastRecordRepository(db_session)
        sample_blast_data["site_id"] = site.id
        blast = blast_repo.create(sample_blast_data)
        
        updated_blast = blast_repo.update_blast_status(blast.id, BlastStatus.APPROVED)
        
        assert updated_blast is not None
        assert updated_blast.blast_status == BlastStatus.APPROVED


class TestMeasurementDataRepository:
    """Test cases for MeasurementDataRepository."""
    
    def test_create_measurement(self, db_session, sample_site_data, sample_blast_data, sample_measurement_data):
        """Test measurement creation."""
        # Create site and blast first
        site_repo = SiteRepository(db_session)
        site = site_repo.create(sample_site_data)
        
        blast_repo = BlastRecordRepository(db_session)
        sample_blast_data["site_id"] = site.id
        blast = blast_repo.create(sample_blast_data)
        
        # Create measurement
        measurement_repo = MeasurementDataRepository(db_session)
        sample_measurement_data["blast_record_id"] = blast.id
        measurement = measurement_repo.create(sample_measurement_data)
        
        assert measurement.id is not None
        assert measurement.measurement_type == MeasurementType.FRAGMENTATION
        assert measurement.get_fragmentation_p80() == 185.3
    
    def test_get_training_data(self, db_session, sample_site_data, sample_blast_data, sample_measurement_data):
        """Test getting training data."""
        # Create site, blast, and measurement
        site_repo = SiteRepository(db_session)
        site = site_repo.create(sample_site_data)
        
        blast_repo = BlastRecordRepository(db_session)
        sample_blast_data["site_id"] = site.id
        blast = blast_repo.create(sample_blast_data)
        
        measurement_repo = MeasurementDataRepository(db_session)
        sample_measurement_data["blast_record_id"] = blast.id
        measurement = measurement_repo.create(sample_measurement_data)
        
        training_data = measurement_repo.get_training_data(MeasurementType.FRAGMENTATION)
        
        assert len(training_data) == 1
        assert training_data[0].id == measurement.id
    
    def test_mark_as_outlier(self, db_session, sample_site_data, sample_blast_data, sample_measurement_data):
        """Test marking measurement as outlier."""
        # Create site, blast, and measurement
        site_repo = SiteRepository(db_session)
        site = site_repo.create(sample_site_data)
        
        blast_repo = BlastRecordRepository(db_session)
        sample_blast_data["site_id"] = site.id
        blast = blast_repo.create(sample_blast_data)
        
        measurement_repo = MeasurementDataRepository(db_session)
        sample_measurement_data["blast_record_id"] = blast.id
        measurement = measurement_repo.create(sample_measurement_data)
        
        updated_measurement = measurement_repo.mark_as_outlier(measurement.id, "Test outlier")
        
        assert updated_measurement is not None
        assert updated_measurement.is_outlier is True
        assert updated_measurement.use_for_training is False


class TestConfigurationRepository:
    """Test cases for ConfigurationRepository."""
    
    def test_create_configuration(self, db_session, sample_config_data):
        """Test configuration creation."""
        repo = ConfigurationRepository(db_session)
        config = repo.create(sample_config_data)
        
        assert config.id is not None
        assert config.config_key == "test_physics_parameters"
        assert config.config_type == ConfigurationType.PHYSICS
        assert config.full_key == "test_physics_parameters"
    
    def test_get_by_key(self, db_session, sample_config_data):
        """Test getting configuration by key."""
        repo = ConfigurationRepository(db_session)
        created_config = repo.create(sample_config_data)
        
        found_config = repo.get_by_key("test_physics_parameters")
        
        assert found_config is not None
        assert found_config.id == created_config.id
    
    def test_get_effective_configuration(self, db_session, sample_config_data):
        """Test getting effective configuration with scope precedence."""
        repo = ConfigurationRepository(db_session)
        
        # Create global config
        global_config = repo.create(sample_config_data)
        
        # Create site-specific config
        site_config_data = sample_config_data.copy()
        site_config_data["config_scope"] = ConfigurationScope.SITE
        site_config_data["site_id"] = 1
        site_config_data["config_value"]["kuz_ram"]["rock_factor_a"] = 6.5
        site_config = repo.create(site_config_data)
        
        # Test global fallback
        effective_global = repo.get_effective_configuration("test_physics_parameters")
        assert effective_global.id == global_config.id
        
        # Test site-specific precedence
        effective_site = repo.get_effective_configuration("test_physics_parameters", site_id=1)
        assert effective_site.id == site_config.id
        assert effective_site.config_value["kuz_ram"]["rock_factor_a"] == 6.5
    
    def test_set_as_default(self, db_session, sample_config_data):
        """Test setting configuration as default."""
        repo = ConfigurationRepository(db_session)
        config = repo.create(sample_config_data)
        
        updated_config = repo.set_as_default(config.id)
        
        assert updated_config is not None
        assert updated_config.is_default is True


if __name__ == "__main__":
    pytest.main([__file__])