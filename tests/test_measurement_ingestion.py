"""
Tests for measurement data ingestion system.
Tests requirements 5.1, 5.2, 5.3: Image upload, PPV parsing, and data storage.
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
import pandas as pd
from fastapi import UploadFile
from io import BytesIO

from src.drill_blast_system.ml_pipeline.data_ingestion import DataIngestionService
from src.drill_blast_system.ml_pipeline.ppv_parser import PPVDataParser, PPVParsingResult
from src.drill_blast_system.ml_pipeline.batch_processor import BatchProcessor, BatchStatus
from src.drill_blast_system.models.measurement_data import MeasurementData, MeasurementType, MeasurementQuality


class TestPPVDataParser:
    """Test PPV data parser functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.parser = PPVDataParser()
    
    def create_test_csv_file(self, data: dict, filename: str = "test_ppv.csv") -> str:
        """Create a test CSV file with PPV data"""
        df = pd.DataFrame(data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df.to_csv(f.name, index=False)
            return f.name
    
    def create_test_text_file(self, lines: list, filename: str = "test_ppv.txt") -> str:
        """Create a test text file with PPV data"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('\n'.join(lines))
            return f.name
    
    def test_parse_csv_file_basic(self):
        """Test basic CSV file parsing"""
        # Create test data
        test_data = {
            'time': np.linspace(0, 10, 1000),
            'vertical': np.sin(2 * np.pi * 10 * np.linspace(0, 10, 1000)) * 2.5,
            'longitudinal': np.sin(2 * np.pi * 8 * np.linspace(0, 10, 1000)) * 1.8,
            'transverse': np.sin(2 * np.pi * 12 * np.linspace(0, 10, 1000)) * 1.2
        }
        
        csv_file = self.create_test_csv_file(test_data)
        
        try:
            result = self.parser.parse_ppv_file(csv_file)
            
            # Verify basic results
            assert isinstance(result, PPVParsingResult)
            assert result.peak_ppv > 0
            assert result.duration > 0
            assert result.sampling_rate > 0
            assert len(result.channels) >= 2  # Should detect at least 2 channels
            assert 'vertical' in result.components
            assert 'longitudinal' in result.components
            
            # Verify peak PPV is reasonable (should be around 1.8 for longitudinal after processing)
            assert 1.0 <= result.peak_ppv <= 3.0
            
        finally:
            os.unlink(csv_file)
    
    def test_parse_text_file_basic(self):
        """Test basic text file parsing"""
        # Create test data lines
        lines = [
            "# PPV Data File",
            "# Sampling Rate: 1000 Hz",
            "# Channels: Time, Vertical, Longitudinal, Transverse",
            "0.000,0.0,0.0,0.0",
            "0.001,1.2,0.8,0.5",
            "0.002,2.1,1.5,0.9",
            "0.003,1.8,1.2,0.7",
            "0.004,0.5,0.3,0.2"
        ]
        
        text_file = self.create_test_text_file(lines)
        
        try:
            result = self.parser.parse_ppv_file(text_file)
            
            # Verify basic results
            assert isinstance(result, PPVParsingResult)
            assert result.peak_ppv > 0
            assert result.duration > 0
            assert len(result.channels) >= 3
            
            # Verify peak PPV matches expected maximum
            assert result.peak_ppv >= 2.1  # Should be at least the max vertical value
            
        finally:
            os.unlink(text_file)
    
    def test_quality_assessment(self):
        """Test PPV data quality assessment"""
        # Create high-quality test data
        test_data = {
            'time': np.linspace(0, 5, 5000),  # Good sampling rate
            'ppv': np.sin(2 * np.pi * 15 * np.linspace(0, 5, 5000)) * 3.2  # Clean signal
        }
        
        csv_file = self.create_test_csv_file(test_data)
        
        try:
            result = self.parser.parse_ppv_file(csv_file)
            
            # Verify quality metrics
            assert result.data_completeness >= 0.9
            assert result.signal_quality in ['excellent', 'good']
            assert not result.interference_detected
            
            # Verify validation checks
            assert len(result.validation_checks) > 0
            pass_checks = [check for check in result.validation_checks if check['status'] == 'PASS']
            assert len(pass_checks) >= 2  # Should pass most checks for good data
            
        finally:
            os.unlink(csv_file)
    
    def test_frequency_analysis(self):
        """Test frequency analysis functionality"""
        # Create test data with known frequency
        freq = 15.0  # Hz
        duration = 2.0  # seconds
        sampling_rate = 1000  # Hz
        samples = int(duration * sampling_rate)
        
        test_data = {
            'time': np.linspace(0, duration, samples),
            'ppv': np.sin(2 * np.pi * freq * np.linspace(0, duration, samples)) * 2.0
        }
        
        csv_file = self.create_test_csv_file(test_data)
        
        try:
            result = self.parser.parse_ppv_file(csv_file)
            
            # Verify frequency analysis
            assert result.dominant_frequency is not None
            assert abs(result.dominant_frequency - freq) < 2.0  # Within 2 Hz tolerance
            assert result.frequency_spectrum is not None
            assert 'frequencies' in result.frequency_spectrum
            assert 'amplitudes' in result.frequency_spectrum
            
        finally:
            os.unlink(csv_file)


class TestDataIngestionService:
    """Test data ingestion service functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = DataIngestionService()
    
    def create_mock_upload_file(self, filename: str, content: bytes, content_type: str = "image/jpeg") -> UploadFile:
        """Create a mock UploadFile for testing"""
        file_obj = BytesIO(content)
        return UploadFile(
            filename=filename,
            file=file_obj,
            size=len(content),
            headers={"content-type": content_type}
        )
    
    @pytest.mark.asyncio
    async def test_validate_fragmentation_inputs(self):
        """Test fragmentation input validation"""
        # Create mock image files
        images = [
            self.create_mock_upload_file("test1.jpg", b"fake_image_data_1"),
            self.create_mock_upload_file("test2.png", b"fake_image_data_2")
        ]
        
        # Mock blast record existence
        with patch('src.drill_blast_system.ml_pipeline.data_ingestion.get_db_session') as mock_db:
            mock_session = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = Mock(id=1)
            mock_db.return_value.__enter__.return_value = mock_session
            
            # Should not raise exception for valid inputs
            await self.service._validate_fragmentation_inputs(images, blast_record_id=1)
    
    @pytest.mark.asyncio
    async def test_validate_fragmentation_inputs_invalid_format(self):
        """Test fragmentation input validation with invalid format"""
        # Create mock file with invalid format
        images = [
            self.create_mock_upload_file("test.txt", b"not_an_image", "text/plain")
        ]
        
        # Mock blast record existence
        with patch('src.drill_blast_system.ml_pipeline.data_ingestion.get_db_session') as mock_db:
            mock_session = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = Mock(id=1)
            mock_db.return_value.__enter__.return_value = mock_session
            
            # Should raise exception for invalid format
            with pytest.raises(ValueError, match="Unsupported image format"):
                await self.service._validate_fragmentation_inputs(images, blast_record_id=1)
    
    @pytest.mark.asyncio
    async def test_validate_ppv_inputs(self):
        """Test PPV input validation"""
        # Create mock PPV files
        ppv_files = [
            self.create_mock_upload_file("sensor1.csv", b"time,ppv\n0,1.2\n1,2.1", "text/csv"),
            self.create_mock_upload_file("sensor2.txt", b"0.0 1.5\n0.1 2.3", "text/plain")
        ]
        
        # Mock blast record existence
        with patch('src.drill_blast_system.ml_pipeline.data_ingestion.get_db_session') as mock_db:
            mock_session = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = Mock(id=1)
            mock_db.return_value.__enter__.return_value = mock_session
            
            # Should not raise exception for valid inputs
            await self.service._validate_ppv_inputs(ppv_files, blast_record_id=1)
    
    @pytest.mark.asyncio
    async def test_save_temp_file(self):
        """Test temporary file saving"""
        # Create mock upload file
        test_content = b"test_file_content"
        upload_file = self.create_mock_upload_file("test.jpg", test_content)
        
        # Save temporary file
        temp_path = await self.service._save_temp_file(upload_file, "test_prefix")
        
        try:
            # Verify file was created and contains correct content
            assert os.path.exists(temp_path)
            with open(temp_path, 'rb') as f:
                saved_content = f.read()
            assert saved_content == test_content
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_store_measurement_file(self):
        """Test permanent file storage"""
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test_measurement_data")
            temp_path = temp_file.name
        
        try:
            # Store file permanently
            stored_path = await self.service._store_measurement_file(
                temp_path, blast_record_id=1, measurement_type="fragmentation_test", 
                original_filename="test.jpg"
            )
            
            # Verify stored path format
            assert "blast_1" in stored_path
            assert "fragmentation_test" in stored_path
            assert stored_path.endswith(".jpg")
            
            # Verify file exists at stored location
            full_stored_path = self.service.storage_base_path / stored_path
            assert full_stored_path.exists()
            
            # Verify content
            with open(full_stored_path, 'rb') as f:
                stored_content = f.read()
            assert stored_content == b"test_measurement_data"
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestBatchProcessor:
    """Test batch processing functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.processor = BatchProcessor(max_concurrent_jobs=2, max_items_per_job=5)
    
    def create_mock_upload_file(self, filename: str, content: bytes, content_type: str = "image/jpeg") -> UploadFile:
        """Create a mock UploadFile for testing"""
        file_obj = BytesIO(content)
        return UploadFile(
            filename=filename,
            file=file_obj,
            size=len(content),
            headers={"content-type": content_type}
        )
    
    @pytest.mark.asyncio
    async def test_submit_batch_job(self):
        """Test batch job submission"""
        # Create mock files
        images = [
            self.create_mock_upload_file("test1.jpg", b"image1"),
            self.create_mock_upload_file("test2.jpg", b"image2")
        ]
        
        ppv_files = [
            self.create_mock_upload_file("sensor1.csv", b"time,ppv\n0,1.2", "text/csv")
        ]
        
        # Mock validation
        with patch.object(self.processor, '_validate_batch_inputs', new_callable=AsyncMock):
            # Submit batch job
            job_id = await self.processor.submit_batch_job(
                blast_record_id=1,
                fragmentation_images=images,
                ppv_files=ppv_files,
                batch_metadata={'operator_name': 'test_operator'}
            )
            
            # Verify job was created
            assert job_id in self.processor.active_jobs
            job = self.processor.active_jobs[job_id]
            assert job.blast_record_id == 1
            assert job.total_items == 3  # 2 images + 1 PPV file
            assert len(job.items) == 3
    
    @pytest.mark.asyncio
    async def test_get_batch_status(self):
        """Test batch status retrieval"""
        # Create a mock job
        job_id = "test_job_123"
        
        # Mock validation and create job manually
        with patch.object(self.processor, '_validate_batch_inputs', new_callable=AsyncMock):
            images = [self.create_mock_upload_file("test.jpg", b"image")]
            await self.processor.submit_batch_job(
                blast_record_id=1,
                fragmentation_images=images
            )
            
            # Get the actual job ID
            actual_job_id = list(self.processor.active_jobs.keys())[0]
            
            # Get status
            status = await self.processor.get_batch_status(actual_job_id)
            
            # Verify status structure
            assert status is not None
            assert 'job_id' in status
            assert 'blast_record_id' in status
            assert 'status' in status
            assert 'total_items' in status
            assert 'item_details' in status
    
    @pytest.mark.asyncio
    async def test_cancel_batch_job(self):
        """Test batch job cancellation"""
        # Create a mock job
        with patch.object(self.processor, '_validate_batch_inputs', new_callable=AsyncMock):
            images = [self.create_mock_upload_file("test.jpg", b"image")]
            job_id = await self.processor.submit_batch_job(
                blast_record_id=1,
                fragmentation_images=images
            )
            
            # Cancel the job
            cancelled = await self.processor.cancel_batch_job(job_id)
            
            # Verify cancellation
            assert cancelled is True
            job = self.processor.active_jobs[job_id]
            assert job.status == BatchStatus.FAILED
            assert "cancelled" in job.error_summary.lower()
    
    @pytest.mark.asyncio
    async def test_validate_batch_inputs_too_many_files(self):
        """Test batch input validation with too many files"""
        # Create more files than allowed
        images = [
            self.create_mock_upload_file(f"test{i}.jpg", b"image") 
            for i in range(self.processor.max_items_per_job + 1)
        ]
        
        # Should raise exception
        with pytest.raises(ValueError, match="Too many files"):
            await self.processor._validate_batch_inputs(images, None, blast_record_id=1)
    
    @pytest.mark.asyncio
    async def test_validate_batch_inputs_no_files(self):
        """Test batch input validation with no files"""
        # Should raise exception for no files
        with pytest.raises(ValueError, match="No files provided"):
            await self.processor._validate_batch_inputs(None, None, blast_record_id=1)


class TestIntegration:
    """Integration tests for measurement ingestion system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_fragmentation_ingestion(self):
        """Test complete fragmentation ingestion workflow"""
        # This would be a more comprehensive test that mocks the entire pipeline
        # from file upload through database storage
        pass
    
    @pytest.mark.asyncio
    async def test_end_to_end_ppv_ingestion(self):
        """Test complete PPV ingestion workflow"""
        # This would test the full PPV processing pipeline
        pass
    
    @pytest.mark.asyncio
    async def test_concurrent_batch_processing(self):
        """Test concurrent processing of multiple batches"""
        # This would test the system's ability to handle multiple concurrent batches
        pass


if __name__ == "__main__":
    pytest.main([__file__])