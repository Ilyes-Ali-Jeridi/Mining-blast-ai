"""
Safety audit trail system for immutable validation history.
Implements requirements 4.3, 4.5, 4.6 for audit trail and validation history.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import hashlib
import logging
from uuid import uuid4

from .models import SafetyValidationResult, SafetyReport

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    """Individual audit trail entry."""
    entry_id: str
    timestamp: datetime
    operation_type: str
    user_id: Optional[str]
    blast_plan_id: Optional[str]
    validation_result: Optional[Dict[str, Any]]
    configuration_snapshot: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    hash_signature: str = ""
    
    def __post_init__(self):
        """Generate hash signature after initialization."""
        if not self.hash_signature:
            self.hash_signature = self._generate_hash()
    
    def _generate_hash(self) -> str:
        """Generate SHA-256 hash of entry content for integrity verification."""
        content = {
            'entry_id': self.entry_id,
            'timestamp': self.timestamp.isoformat(),
            'operation_type': self.operation_type,
            'user_id': self.user_id,
            'blast_plan_id': self.blast_plan_id,
            'validation_result': self.validation_result,
            'configuration_snapshot': self.configuration_snapshot,
            'metadata': self.metadata
        }
        
        content_str = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """Verify entry integrity by recalculating hash."""
        expected_hash = self._generate_hash()
        return self.hash_signature == expected_hash
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


@dataclass
class ValidationHistory:
    """History of safety validations for a blast plan."""
    blast_plan_id: str
    validations: List[AuditEntry] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_validation(self, entry: AuditEntry) -> None:
        """Add validation entry to history."""
        self.validations.append(entry)
        self.validations.sort(key=lambda x: x.timestamp)
    
    def get_latest_validation(self) -> Optional[AuditEntry]:
        """Get most recent validation entry."""
        return self.validations[-1] if self.validations else None
    
    def get_validation_by_id(self, entry_id: str) -> Optional[AuditEntry]:
        """Get validation entry by ID."""
        for entry in self.validations:
            if entry.entry_id == entry_id:
                return entry
        return None
    
    def verify_chain_integrity(self) -> bool:
        """Verify integrity of entire validation chain."""
        for entry in self.validations:
            if not entry.verify_integrity():
                logger.error(f"Integrity check failed for entry {entry.entry_id}")
                return False
        return True


class SafetyAuditTrail:
    """Immutable audit trail for all safety validations."""
    
    def __init__(self, audit_dir: Optional[Path] = None):
        """Initialize audit trail with storage directory."""
        self.audit_dir = audit_dir or Path("audit/safety")
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.audit_dir / "validations").mkdir(exist_ok=True)
        (self.audit_dir / "configurations").mkdir(exist_ok=True)
        (self.audit_dir / "reports").mkdir(exist_ok=True)
        (self.audit_dir / "integrity").mkdir(exist_ok=True)
    
    def record_validation(self, 
                         validation_result: SafetyValidationResult,
                         blast_plan_id: str,
                         user_id: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Record safety validation in immutable audit trail.
        
        Args:
            validation_result: Complete validation result
            blast_plan_id: Unique blast plan identifier
            user_id: User who performed validation
            metadata: Additional metadata
            
        Returns:
            Audit entry ID
        """
        entry_id = str(uuid4())
        
        # Create audit entry
        entry = AuditEntry(
            entry_id=entry_id,
            timestamp=validation_result.validation_timestamp,
            operation_type="safety_validation",
            user_id=user_id,
            blast_plan_id=blast_plan_id,
            validation_result=validation_result.to_dict(),
            configuration_snapshot=validation_result.safety_config_snapshot,
            metadata=metadata or {}
        )
        
        # Store entry
        self._store_audit_entry(entry)
        
        # Update validation history
        self._update_validation_history(blast_plan_id, entry)
        
        # Store integrity checkpoint
        self._store_integrity_checkpoint(entry)
        
        logger.info(f"Recorded safety validation audit entry: {entry_id}")
        return entry_id
    
    def record_configuration_change(self,
                                  old_config: Dict[str, Any],
                                  new_config: Dict[str, Any],
                                  user_id: Optional[str] = None,
                                  change_reason: str = "") -> str:
        """Record safety configuration change."""
        entry_id = str(uuid4())
        
        entry = AuditEntry(
            entry_id=entry_id,
            timestamp=datetime.utcnow(),
            operation_type="config_change",
            user_id=user_id,
            blast_plan_id=None,
            validation_result=None,
            configuration_snapshot=new_config,
            metadata={
                'old_config': old_config,
                'change_reason': change_reason,
                'config_diff': self._calculate_config_diff(old_config, new_config)
            }
        )
        
        self._store_audit_entry(entry)
        self._store_integrity_checkpoint(entry)
        
        logger.info(f"Recorded configuration change audit entry: {entry_id}")
        return entry_id
    
    def record_sign_off(self,
                       blast_plan_id: str,
                       engineer_name: str,
                       engineer_id: str,
                       validation_id: str,
                       certification_statement: str,
                       user_id: Optional[str] = None) -> str:
        """Record engineer sign-off for blast plan."""
        entry_id = str(uuid4())
        
        entry = AuditEntry(
            entry_id=entry_id,
            timestamp=datetime.utcnow(),
            operation_type="engineer_signoff",
            user_id=user_id,
            blast_plan_id=blast_plan_id,
            validation_result=None,
            configuration_snapshot={},
            metadata={
                'engineer_name': engineer_name,
                'engineer_id': engineer_id,
                'validation_id': validation_id,
                'certification_statement': certification_statement,
                'digital_signature': self._generate_digital_signature(
                    blast_plan_id, engineer_id, validation_id
                )
            }
        )
        
        self._store_audit_entry(entry)
        self._update_validation_history(blast_plan_id, entry)
        self._store_integrity_checkpoint(entry)
        
        logger.info(f"Recorded engineer sign-off audit entry: {entry_id}")
        return entry_id
    
    def get_validation_history(self, blast_plan_id: str) -> ValidationHistory:
        """Get complete validation history for blast plan."""
        history_file = self.audit_dir / "validations" / f"{blast_plan_id}.json"
        
        if not history_file.exists():
            return ValidationHistory(blast_plan_id=blast_plan_id)
        
        try:
            with open(history_file, 'r') as f:
                data = json.load(f)
            
            # Reconstruct validation history
            history = ValidationHistory(
                blast_plan_id=data['blast_plan_id'],
                created_at=datetime.fromisoformat(data['created_at'])
            )
            
            for entry_data in data['validations']:
                entry = AuditEntry(
                    entry_id=entry_data['entry_id'],
                    timestamp=datetime.fromisoformat(entry_data['timestamp']),
                    operation_type=entry_data['operation_type'],
                    user_id=entry_data.get('user_id'),
                    blast_plan_id=entry_data.get('blast_plan_id'),
                    validation_result=entry_data.get('validation_result'),
                    configuration_snapshot=entry_data['configuration_snapshot'],
                    metadata=entry_data.get('metadata', {}),
                    hash_signature=entry_data['hash_signature']
                )
                history.add_validation(entry)
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to load validation history for {blast_plan_id}: {e}")
            return ValidationHistory(blast_plan_id=blast_plan_id)
    
    def get_audit_entry(self, entry_id: str) -> Optional[AuditEntry]:
        """Get specific audit entry by ID."""
        entry_file = self.audit_dir / "entries" / f"{entry_id}.json"
        
        if not entry_file.exists():
            return None
        
        try:
            with open(entry_file, 'r') as f:
                data = json.load(f)
            
            return AuditEntry(
                entry_id=data['entry_id'],
                timestamp=datetime.fromisoformat(data['timestamp']),
                operation_type=data['operation_type'],
                user_id=data.get('user_id'),
                blast_plan_id=data.get('blast_plan_id'),
                validation_result=data.get('validation_result'),
                configuration_snapshot=data['configuration_snapshot'],
                metadata=data.get('metadata', {}),
                hash_signature=data['hash_signature']
            )
            
        except Exception as e:
            logger.error(f"Failed to load audit entry {entry_id}: {e}")
            return None
    
    def verify_audit_integrity(self, blast_plan_id: Optional[str] = None) -> Dict[str, Any]:
        """Verify integrity of audit trail."""
        results = {
            'overall_status': 'VALID',
            'total_entries': 0,
            'verified_entries': 0,
            'failed_entries': [],
            'missing_entries': [],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if blast_plan_id:
            # Verify specific blast plan history
            history = self.get_validation_history(blast_plan_id)
            results['total_entries'] = len(history.validations)
            
            for entry in history.validations:
                if entry.verify_integrity():
                    results['verified_entries'] += 1
                else:
                    results['failed_entries'].append(entry.entry_id)
                    results['overall_status'] = 'COMPROMISED'
        else:
            # Verify all entries
            entries_dir = self.audit_dir / "entries"
            if entries_dir.exists():
                for entry_file in entries_dir.glob("*.json"):
                    entry = self.get_audit_entry(entry_file.stem)
                    if entry:
                        results['total_entries'] += 1
                        if entry.verify_integrity():
                            results['verified_entries'] += 1
                        else:
                            results['failed_entries'].append(entry.entry_id)
                            results['overall_status'] = 'COMPROMISED'
        
        logger.info(f"Audit integrity check: {results['verified_entries']}/{results['total_entries']} verified")
        return results
    
    def generate_compliance_report(self, 
                                 blast_plan_id: str,
                                 include_full_history: bool = True) -> Dict[str, Any]:
        """Generate compliance report for regulatory purposes."""
        history = self.get_validation_history(blast_plan_id)
        
        report = {
            'blast_plan_id': blast_plan_id,
            'report_generated': datetime.utcnow().isoformat(),
            'total_validations': len(history.validations),
            'validation_summary': {},
            'sign_off_status': 'PENDING',
            'compliance_status': 'UNKNOWN',
            'audit_trail_integrity': 'UNKNOWN'
        }
        
        if history.validations:
            # Find latest safety validation entry (not sign-off or config change)
            validation_entries = [e for e in history.validations if e.operation_type == 'safety_validation']
            latest = max(validation_entries, key=lambda x: x.timestamp) if validation_entries else None
            if latest and latest.validation_result:
                validation_data = latest.validation_result
                report['validation_summary'] = {
                    'is_valid': validation_data.get('is_valid', False),
                    'total_checks': len(validation_data.get('safety_checks', [])),
                    'failed_checks': len([c for c in validation_data.get('safety_checks', []) 
                                        if c.get('status') == 'FAIL']),
                    'violations': len(validation_data.get('violations', [])),
                    'last_validation': latest.timestamp.isoformat()
                }
                
                report['compliance_status'] = 'COMPLIANT' if validation_data.get('is_valid') else 'NON_COMPLIANT'
        
        # Check for sign-off
        sign_off_entries = [e for e in history.validations if e.operation_type == 'engineer_signoff']
        if sign_off_entries:
            latest_signoff = max(sign_off_entries, key=lambda x: x.timestamp)
            report['sign_off_status'] = 'SIGNED'
            report['sign_off_details'] = {
                'engineer_name': latest_signoff.metadata.get('engineer_name'),
                'engineer_id': latest_signoff.metadata.get('engineer_id'),
                'sign_off_time': latest_signoff.timestamp.isoformat()
            }
        
        # Verify integrity
        integrity_check = self.verify_audit_integrity(blast_plan_id)
        report['audit_trail_integrity'] = integrity_check['overall_status']
        
        if include_full_history:
            report['full_history'] = [entry.to_dict() for entry in history.validations]
        
        return report
    
    def _store_audit_entry(self, entry: AuditEntry) -> None:
        """Store individual audit entry."""
        entries_dir = self.audit_dir / "entries"
        entries_dir.mkdir(exist_ok=True)
        
        entry_file = entries_dir / f"{entry.entry_id}.json"
        
        with open(entry_file, 'w') as f:
            json.dump(entry.to_dict(), f, indent=2, default=str)
    
    def _update_validation_history(self, blast_plan_id: str, entry: AuditEntry) -> None:
        """Update validation history for blast plan."""
        history = self.get_validation_history(blast_plan_id)
        history.add_validation(entry)
        
        history_file = self.audit_dir / "validations" / f"{blast_plan_id}.json"
        
        history_data = {
            'blast_plan_id': history.blast_plan_id,
            'created_at': history.created_at.isoformat(),
            'validations': [entry.to_dict() for entry in history.validations]
        }
        
        with open(history_file, 'w') as f:
            json.dump(history_data, f, indent=2, default=str)
    
    def _store_integrity_checkpoint(self, entry: AuditEntry) -> None:
        """Store integrity checkpoint for entry."""
        checkpoint_file = self.audit_dir / "integrity" / f"{entry.entry_id}.hash"
        
        checkpoint_data = {
            'entry_id': entry.entry_id,
            'timestamp': entry.timestamp.isoformat(),
            'hash_signature': entry.hash_signature,
            'checkpoint_time': datetime.utcnow().isoformat()
        }
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
    
    def _calculate_config_diff(self, old_config: Dict[str, Any], 
                              new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate differences between configurations."""
        diff = {
            'added': {},
            'removed': {},
            'modified': {}
        }
        
        # Find added and modified keys
        for key, new_value in new_config.items():
            if key not in old_config:
                diff['added'][key] = new_value
            elif old_config[key] != new_value:
                diff['modified'][key] = {
                    'old': old_config[key],
                    'new': new_value
                }
        
        # Find removed keys
        for key, old_value in old_config.items():
            if key not in new_config:
                diff['removed'][key] = old_value
        
        return diff
    
    def _generate_digital_signature(self, blast_plan_id: str, 
                                   engineer_id: str, validation_id: str) -> str:
        """Generate digital signature for sign-off."""
        signature_data = f"{blast_plan_id}:{engineer_id}:{validation_id}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(signature_data.encode()).hexdigest()