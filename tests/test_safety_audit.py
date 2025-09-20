"""
Tests for safety audit trail system.
Validates requirements 4.3, 4.5, 4.6 for immutable audit trails.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import json
from pathlib import Path
import hashlib

from src.drill_blast_system.safety.audit import (
    SafetyAuditTrail, AuditEntry, ValidationHistory
)
from src.drill_blast_system.safety.models import (
    SafetyValidationResult, SafetyCheck, SafetyViolation, SafetyStatus,
    SafetyCheckType, ViolationSeverity
)


@pytest.fixture
def audit_trail(tmp_path):
    """Create audit trail with temporary directory."""
    return SafetyAuditTrail(audit_dir=tmp_path / "audit")


@pytest.fixture
def sample_validation_result():
    """Create sample validation result for testing."""
    safety_checks = [
        SafetyCheck(
            check_name="Test Check 1",
            check_type=SafetyCheckType.CHARGE_PER_HOLE,
            status=SafetyStatus.PASS,
            limit_value=50.0,
            actual_value=30.0,
            safety_margin=0.4,
            description="Test check passed",
            units="kg"
        )
    ]
    
    return SafetyValidationResult(
        validation_timestamp=datetime.utcnow(),
        is_valid=True,
        safety_checks=safety_checks,
        violations=[],
        safety_config_snapshot={'max_charge_per_hole': 50.0}
    )


@pytest.fixture
def sample_audit_entry():
    """Create sample audit entry for testing."""
    return AuditEntry(
        entry_id="test_entry_001",
        timestamp=datetime.utcnow(),
        operation_type="safety_validation",
        user_id="test_user",
        blast_plan_id="test_plan_001",
        validation_result={'is_valid': True, 'violations': []},
        configuration_snapshot={'version': '1.0.0'},
        metadata={'test_key': 'test_value'}
    )


class TestAuditEntry:
    """Test audit entry functionality."""
    
    def test_audit_entry_creation(self, sample_audit_entry):
        """Test audit entry creation and hash generation."""
        entry = sample_audit_entry
        
        assert entry.entry_id == "test_entry_001"
        assert entry.operation_type == "safety_validation"
        assert entry.hash_signature is not None
        assert len(entry.hash_signature) == 64  # SHA-256 hex length
    
    def test_hash_generation_consistency(self, sample_audit_entry):
        """Test that hash generation is consistent."""
        entry = sample_audit_entry
        original_hash = entry.hash_signature
        
        # Regenerate hash
        new_hash = entry._generate_hash()
        
        assert original_hash == new_hash
    
    def test_integrity_verification(self, sample_audit_entry):
        """Test audit entry integrity verification."""
        entry = sample_audit_entry
        
        # Should verify successfully
        assert entry.verify_integrity()
        
        # Tamper with entry
        entry.metadata['tampered'] = 'true'
        
        # Should fail verification (hash doesn't match modified content)
        assert not entry.verify_integrity()
    
    def test_to_dict_conversion(self, sample_audit_entry):
        """Test conversion to dictionary."""
        entry = sample_audit_entry
        entry_dict = entry.to_dict()
        
        assert isinstance(entry_dict, dict)
        assert entry_dict['entry_id'] == entry.entry_id
        assert entry_dict['operation_type'] == entry.operation_type
        assert entry_dict['hash_signature'] == entry.hash_signature
    
    def test_hash_changes_with_content(self):
        """Test that hash changes when content changes."""
        entry1 = AuditEntry(
            entry_id="test_001",
            timestamp=datetime.utcnow(),
            operation_type="safety_validation",
            user_id="user1",
            blast_plan_id="plan1",
            validation_result={'result': 'pass'},
            configuration_snapshot={'config': 'v1'},
            metadata={}
        )
        
        entry2 = AuditEntry(
            entry_id="test_002",  # Different ID
            timestamp=entry1.timestamp,
            operation_type="safety_validation",
            user_id="user1",
            blast_plan_id="plan1",
            validation_result={'result': 'pass'},
            configuration_snapshot={'config': 'v1'},
            metadata={}
        )
        
        assert entry1.hash_signature != entry2.hash_signature


class TestValidationHistory:
    """Test validation history functionality."""
    
    def test_validation_history_creation(self):
        """Test validation history creation."""
        blast_plan_id = "test_plan_001"
        history = ValidationHistory(blast_plan_id=blast_plan_id)
        
        assert history.blast_plan_id == blast_plan_id
        assert len(history.validations) == 0
        assert isinstance(history.created_at, datetime)
    
    def test_add_validation_entry(self, sample_audit_entry):
        """Test adding validation entries."""
        history = ValidationHistory(blast_plan_id="test_plan")
        
        assert len(history.validations) == 0
        
        history.add_validation(sample_audit_entry)
        
        assert len(history.validations) == 1
        assert history.validations[0] == sample_audit_entry
    
    def test_validation_sorting(self):
        """Test that validations are sorted by timestamp."""
        history = ValidationHistory(blast_plan_id="test_plan")
        
        # Add entries in reverse chronological order
        now = datetime.utcnow()
        
        entry1 = AuditEntry(
            entry_id="entry_1",
            timestamp=now - timedelta(hours=2),
            operation_type="safety_validation",
            user_id="user1",
            blast_plan_id="test_plan",
            validation_result={},
            configuration_snapshot={},
            metadata={}
        )
        
        entry2 = AuditEntry(
            entry_id="entry_2",
            timestamp=now - timedelta(hours=1),
            operation_type="safety_validation",
            user_id="user1",
            blast_plan_id="test_plan",
            validation_result={},
            configuration_snapshot={},
            metadata={}
        )
        
        entry3 = AuditEntry(
            entry_id="entry_3",
            timestamp=now,
            operation_type="safety_validation",
            user_id="user1",
            blast_plan_id="test_plan",
            validation_result={},
            configuration_snapshot={},
            metadata={}
        )
        
        # Add in reverse order
        history.add_validation(entry3)
        history.add_validation(entry1)
        history.add_validation(entry2)
        
        # Should be sorted chronologically
        assert history.validations[0] == entry1
        assert history.validations[1] == entry2
        assert history.validations[2] == entry3
    
    def test_get_latest_validation(self):
        """Test getting latest validation entry."""
        history = ValidationHistory(blast_plan_id="test_plan")
        
        # No validations
        assert history.get_latest_validation() is None
        
        # Add validation
        entry = AuditEntry(
            entry_id="latest",
            timestamp=datetime.utcnow(),
            operation_type="safety_validation",
            user_id="user1",
            blast_plan_id="test_plan",
            validation_result={},
            configuration_snapshot={},
            metadata={}
        )
        
        history.add_validation(entry)
        
        assert history.get_latest_validation() == entry
    
    def test_get_validation_by_id(self, sample_audit_entry):
        """Test getting validation by ID."""
        history = ValidationHistory(blast_plan_id="test_plan")
        history.add_validation(sample_audit_entry)
        
        # Should find entry
        found_entry = history.get_validation_by_id(sample_audit_entry.entry_id)
        assert found_entry == sample_audit_entry
        
        # Should not find non-existent entry
        not_found = history.get_validation_by_id("non_existent")
        assert not_found is None
    
    def test_verify_chain_integrity(self):
        """Test verification of entire validation chain integrity."""
        history = ValidationHistory(blast_plan_id="test_plan")
        
        # Empty chain should be valid
        assert history.verify_chain_integrity()
        
        # Add valid entries
        entry1 = AuditEntry(
            entry_id="entry_1",
            timestamp=datetime.utcnow(),
            operation_type="safety_validation",
            user_id="user1",
            blast_plan_id="test_plan",
            validation_result={},
            configuration_snapshot={},
            metadata={}
        )
        
        entry2 = AuditEntry(
            entry_id="entry_2",
            timestamp=datetime.utcnow(),
            operation_type="safety_validation",
            user_id="user1",
            blast_plan_id="test_plan",
            validation_result={},
            configuration_snapshot={},
            metadata={}
        )
        
        history.add_validation(entry1)
        history.add_validation(entry2)
        
        # Should verify successfully
        assert history.verify_chain_integrity()
        
        # Tamper with one entry
        entry1.metadata['tampered'] = True
        
        # Should fail verification
        assert not history.verify_chain_integrity()


class TestSafetyAuditTrail:
    """Test safety audit trail functionality."""
    
    def test_audit_trail_initialization(self, tmp_path):
        """Test audit trail initialization."""
        audit_dir = tmp_path / "test_audit"
        trail = SafetyAuditTrail(audit_dir=audit_dir)
        
        assert trail.audit_dir == audit_dir
        assert audit_dir.exists()
        
        # Check subdirectories
        assert (audit_dir / "validations").exists()
        assert (audit_dir / "configurations").exists()
        assert (audit_dir / "reports").exists()
        assert (audit_dir / "integrity").exists()
    
    def test_record_validation(self, audit_trail, sample_validation_result):
        """Test recording safety validation."""
        blast_plan_id = "test_plan_001"
        user_id = "test_user"
        
        entry_id = audit_trail.record_validation(
            sample_validation_result, blast_plan_id, user_id
        )
        
        assert entry_id is not None
        assert isinstance(entry_id, str)
        
        # Verify entry was stored
        entry = audit_trail.get_audit_entry(entry_id)
        assert entry is not None
        assert entry.blast_plan_id == blast_plan_id
        assert entry.user_id == user_id
        assert entry.operation_type == "safety_validation"
    
    def test_record_configuration_change(self, audit_trail):
        """Test recording configuration changes."""
        old_config = {'max_charge_per_hole': 50.0, 'version': '1.0.0'}
        new_config = {'max_charge_per_hole': 45.0, 'version': '1.1.0'}
        user_id = "admin_user"
        change_reason = "Regulatory update"
        
        entry_id = audit_trail.record_configuration_change(
            old_config, new_config, user_id, change_reason
        )
        
        assert entry_id is not None
        
        # Verify entry
        entry = audit_trail.get_audit_entry(entry_id)
        assert entry is not None
        assert entry.operation_type == "config_change"
        assert entry.user_id == user_id
        assert entry.metadata['change_reason'] == change_reason
        assert 'config_diff' in entry.metadata
    
    def test_record_sign_off(self, audit_trail):
        """Test recording engineer sign-off."""
        blast_plan_id = "test_plan_001"
        engineer_name = "John Engineer"
        engineer_id = "ENG001"
        validation_id = "validation_123"
        certification = "I certify this blast plan meets all safety requirements"
        
        entry_id = audit_trail.record_sign_off(
            blast_plan_id, engineer_name, engineer_id, 
            validation_id, certification
        )
        
        assert entry_id is not None
        
        # Verify entry
        entry = audit_trail.get_audit_entry(entry_id)
        assert entry is not None
        assert entry.operation_type == "engineer_signoff"
        assert entry.blast_plan_id == blast_plan_id
        assert entry.metadata['engineer_name'] == engineer_name
        assert entry.metadata['engineer_id'] == engineer_id
        assert entry.metadata['validation_id'] == validation_id
        assert 'digital_signature' in entry.metadata
    
    def test_get_validation_history(self, audit_trail, sample_validation_result):
        """Test retrieving validation history."""
        blast_plan_id = "test_plan_history"
        
        # Initially empty
        history = audit_trail.get_validation_history(blast_plan_id)
        assert history.blast_plan_id == blast_plan_id
        assert len(history.validations) == 0
        
        # Add some validations
        for i in range(3):
            audit_trail.record_validation(
                sample_validation_result, blast_plan_id, f"user_{i}"
            )
        
        # Retrieve history
        history = audit_trail.get_validation_history(blast_plan_id)
        assert len(history.validations) == 3
        
        # Should be sorted by timestamp
        timestamps = [v.timestamp for v in history.validations]
        assert timestamps == sorted(timestamps)
    
    def test_get_audit_entry(self, audit_trail, sample_validation_result):
        """Test retrieving specific audit entry."""
        blast_plan_id = "test_plan_entry"
        
        entry_id = audit_trail.record_validation(
            sample_validation_result, blast_plan_id, "test_user"
        )
        
        # Retrieve entry
        entry = audit_trail.get_audit_entry(entry_id)
        assert entry is not None
        assert entry.entry_id == entry_id
        assert entry.blast_plan_id == blast_plan_id
        
        # Non-existent entry
        non_existent = audit_trail.get_audit_entry("non_existent_id")
        assert non_existent is None
    
    def test_verify_audit_integrity(self, audit_trail, sample_validation_result):
        """Test audit trail integrity verification."""
        blast_plan_id = "test_plan_integrity"
        
        # Record some validations
        entry_ids = []
        for i in range(3):
            entry_id = audit_trail.record_validation(
                sample_validation_result, blast_plan_id, f"user_{i}"
            )
            entry_ids.append(entry_id)
        
        # Verify integrity for specific blast plan
        integrity_result = audit_trail.verify_audit_integrity(blast_plan_id)
        
        assert integrity_result['overall_status'] == 'VALID'
        assert integrity_result['total_entries'] == 3
        assert integrity_result['verified_entries'] == 3
        assert len(integrity_result['failed_entries']) == 0
        
        # Verify system-wide integrity
        system_integrity = audit_trail.verify_audit_integrity()
        assert system_integrity['overall_status'] == 'VALID'
        assert system_integrity['total_entries'] >= 3
    
    def test_generate_compliance_report(self, audit_trail, sample_validation_result):
        """Test compliance report generation."""
        blast_plan_id = "test_plan_compliance"
        
        # Record validation and sign-off
        validation_entry_id = audit_trail.record_validation(
            sample_validation_result, blast_plan_id, "test_user"
        )
        
        signoff_entry_id = audit_trail.record_sign_off(
            blast_plan_id, "John Engineer", "ENG001", 
            validation_entry_id, "Certified safe"
        )
        
        # Generate compliance report
        report = audit_trail.generate_compliance_report(blast_plan_id)
        
        assert report['blast_plan_id'] == blast_plan_id
        assert report['total_validations'] == 1
        assert report['compliance_status'] == 'COMPLIANT'  # Valid validation
        assert report['sign_off_status'] == 'SIGNED'
        assert report['audit_trail_integrity'] == 'VALID'
        
        # Check sign-off details
        assert 'sign_off_details' in report
        assert report['sign_off_details']['engineer_name'] == "John Engineer"
    
    def test_digital_signature_generation(self, audit_trail):
        """Test digital signature generation for sign-offs."""
        blast_plan_id = "test_plan_sig"
        engineer_id = "ENG001"
        validation_id = "val_123"
        
        # Generate signature
        signature = audit_trail._generate_digital_signature(
            blast_plan_id, engineer_id, validation_id
        )
        
        assert signature is not None
        assert len(signature) == 64  # SHA-256 hex length
        
        # Same inputs should generate same signature
        signature2 = audit_trail._generate_digital_signature(
            blast_plan_id, engineer_id, validation_id
        )
        
        # Note: Signatures will be different due to timestamp inclusion
        # This is intentional for security
        assert len(signature2) == 64
    
    def test_config_diff_calculation(self, audit_trail):
        """Test configuration difference calculation."""
        old_config = {
            'max_charge_per_hole': 50.0,
            'ppv_limit': 5.0,
            'version': '1.0.0'
        }
        
        new_config = {
            'max_charge_per_hole': 45.0,  # Modified
            'ppv_limit': 5.0,             # Unchanged
            'version': '1.1.0',           # Modified
            'new_parameter': 10.0         # Added
        }
        
        diff = audit_trail._calculate_config_diff(old_config, new_config)
        
        assert 'added' in diff
        assert 'removed' in diff
        assert 'modified' in diff
        
        assert 'new_parameter' in diff['added']
        assert 'max_charge_per_hole' in diff['modified']
        assert 'version' in diff['modified']
        
        # ppv_limit should not appear in any category (unchanged)
        assert 'ppv_limit' not in diff['added']
        assert 'ppv_limit' not in diff['removed']
        assert 'ppv_limit' not in diff['modified']
    
    def test_audit_trail_persistence(self, audit_trail, sample_validation_result):
        """Test that audit trail persists across instances."""
        blast_plan_id = "test_plan_persist"
        
        # Record validation
        entry_id = audit_trail.record_validation(
            sample_validation_result, blast_plan_id, "test_user"
        )
        
        # Create new audit trail instance with same directory
        new_trail = SafetyAuditTrail(audit_dir=audit_trail.audit_dir)
        
        # Should be able to retrieve the entry
        entry = new_trail.get_audit_entry(entry_id)
        assert entry is not None
        assert entry.entry_id == entry_id
        
        # Should be able to retrieve history
        history = new_trail.get_validation_history(blast_plan_id)
        assert len(history.validations) == 1
    
    def test_integrity_checkpoint_storage(self, audit_trail, sample_validation_result):
        """Test integrity checkpoint storage."""
        blast_plan_id = "test_plan_checkpoint"
        
        entry_id = audit_trail.record_validation(
            sample_validation_result, blast_plan_id, "test_user"
        )
        
        # Check that integrity checkpoint was created
        checkpoint_file = audit_trail.audit_dir / "integrity" / f"{entry_id}.hash"
        assert checkpoint_file.exists()
        
        # Verify checkpoint content
        with open(checkpoint_file, 'r') as f:
            checkpoint_data = json.load(f)
        
        assert checkpoint_data['entry_id'] == entry_id
        assert 'hash_signature' in checkpoint_data
        assert 'checkpoint_time' in checkpoint_data
    
    def test_compliance_report_with_violations(self, audit_trail):
        """Test compliance report with validation violations."""
        blast_plan_id = "test_plan_violations"
        
        # Create validation result with violations
        violation_result = SafetyValidationResult(
            validation_timestamp=datetime.utcnow(),
            is_valid=False,
            safety_checks=[],
            violations=[
                SafetyViolation(
                    violation_type=SafetyCheckType.CHARGE_PER_HOLE.value,
                    severity=ViolationSeverity.CRITICAL,
                    description="Charge exceeds limit",
                    suggested_mitigation="Reduce charge"
                )
            ],
            safety_config_snapshot={'version': '1.0.0'}
        )
        
        audit_trail.record_validation(violation_result, blast_plan_id, "test_user")
        
        report = audit_trail.generate_compliance_report(blast_plan_id)
        
        assert report['compliance_status'] == 'NON_COMPLIANT'
        assert report['validation_summary']['is_valid'] == False
        assert report['validation_summary']['violations'] == 1
        assert report['sign_off_status'] == 'PENDING'  # No sign-off recorded